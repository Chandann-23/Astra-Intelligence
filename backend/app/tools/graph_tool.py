from langchain.tools import tool
from neo4j import GraphDatabase
import os
import re
from dotenv import load_dotenv

load_dotenv()

class Neo4jManager:
    def __init__(self):
        # Fallbacks to local defaults if .env isn't loaded
        # Production: Use neo4j+s:// protocol for secure AuraDB connections
        self.uri = os.getenv("NEO4J_URI", "neo4j+s://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password123")
        self._driver = None
        self._model = None
        self._index_initialized = False
        print("Neo4jManager initialized (Lazy Mode).")

    @property
    def driver(self):
        """Lazy loader for Neo4j driver to prevent blocking at startup."""
        if self._driver is None:
            try:
                # We only create the driver instance here. 
                # We do NOT call verify_connectivity() as it's a blocking network call 
                # that can cause Render port timeouts during startup.
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            except Exception as e:
                print(f"CRITICAL: Could not initialize Neo4j driver for {self.uri}: {e}")
        return self._driver

    @property
    def model(self):
        """Lazy loader for SentenceTransformer to save RAM."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print("Loading SentenceTransformer model...")
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"ERROR: Failed to load SentenceTransformer: {e}")
        return self._model

    def ensure_index(self):
        """Ensures the vector index is initialized once."""
        if not self._index_initialized and self.driver:
            try:
                self.create_vector_index()
                if self.verify_index():
                    print("SUCCESS: Vector Index 'concept_embeddings' is ONLINE.")
                    self._index_initialized = True
            except Exception as e:
                print(f"WARNING: Index initialization deferred: {e}")

    def close(self):
        if self._driver:
            self._driver.close()

    def create_vector_index(self):
        if not self.driver: return
        with self.driver.session() as session:
            # 2026 syntax for vector index
            query = """
            CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS
            FOR (n:Concept)
            ON (n.embedding)
            OPTIONS {
              indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
              }
            }
            """
            try:
                session.run(query)
                print("Vector index initialization command sent.")
            except Exception as e:
                print(f"Index creation skipped/failed: {e}")

    def verify_index(self):
        """
        Confirms the concept_embeddings index is ONLINE.
        """
        if not self.driver: return False
        with self.driver.session() as session:
            query = "SHOW INDEXES YIELD name, type, state WHERE name = 'concept_embeddings'"
            result = session.run(query)
            record = result.single()
            if record and record['state'] == 'ONLINE':
                return True
            return False

    def upsert_relationship(self, source_node: str, relationship: str, target_node: str, properties: dict = None):
        """
        Creates or updates a relationship between two nodes with ON CREATE embedding logic.
        """
        self.ensure_index()
        if not self.driver: return
        
        # Ensure dimensions match (MiniLM-L6-v2 produces 384)
        source_embedding = self.model.encode(source_node).tolist()
        target_embedding = self.model.encode(target_node).tolist()
        
        clean_rel = "".join(e for e in relationship if e.isalnum() or e == '_').upper()
        
        with self.driver.session() as session:
            query = (
                "MERGE (s:Concept {name: $source}) "
                "ON CREATE SET s.embedding = $source_emb "
                "MERGE (t:Concept {name: $target}) "
                "ON CREATE SET t.embedding = $target_emb "
                f"MERGE (s)-[r:{clean_rel}]->(t) "
                "SET r += $props "
                "RETURN s, r, t"
            )
            session.run(
                query, 
                source=source_node, 
                source_emb=source_embedding,
                target=target_node, 
                target_emb=target_embedding,
                props=properties or {}
            )

    def vector_search(self, query: str, top_k: int = 5):
        """
        Performs a Vector Similarity Search in Neo4j and retrieves neighbors with reasoning.
        """
        self.ensure_index()
        if not self.driver: return [], "Database offline."
        
        query_embedding = self.model.encode(query).tolist()
        
        with self.driver.session() as session:
            # Cypher for Vector Search + Neighbors + Scores for reasoning
            search_query = """
            CALL db.index.vector.queryNodes('concept_embeddings', $k, $query_emb)
            YIELD node, score
            MATCH (node)-[r]-(neighbor:Concept)
            RETURN node.name as entity, type(r) as relationship, neighbor.name as connected_to, score
            ORDER BY score DESC
            LIMIT 15
            """
            result = session.run(search_query, query_emb=query_embedding, k=top_k)
            
            knowledge_bits = []
            top_score = 0
            best_match = ""
            
            for record in result:
                bit = f"[{record['entity']}] --({record['relationship']})--> [{record['connected_to']}]"
                if bit not in knowledge_bits:
                    knowledge_bits.append(bit)
                if record['score'] > top_score:
                    top_score = record['score']
                    best_match = record['entity']
            
            reasoning = f"Reasoning: Retrieved nodes based on semantic proximity to '{query}'. Best match found was '{best_match}' with a confidence score of {top_score:.2f}."
            
            return knowledge_bits, reasoning

    def get_all_data(self):
        """
        Retrieves all nodes and relationships for visualization.
        """
        if not self.driver: return {"nodes": [], "links": []}
        with self.driver.session() as session:
            query = (
                "MATCH (n:Concept)-[r]->(m:Concept) "
                "RETURN n.name as source_name, type(r) as rel_type, m.name as target_name"
            )
            result = session.run(query)
            
            nodes = set()
            links = []
            
            for record in result:
                source = record["source_name"]
                target = record["target_name"]
                rel = record["rel_type"]
                
                nodes.add(source)
                nodes.add(target)
                links.append({
                    "source": source,
                    "target": target,
                    "label": rel
                })
            
            return {
                "nodes": [{"id": name, "name": name} for name in nodes],
                "links": links
            }

# Global instance for the tool to use
neo4j_manager = Neo4jManager()

@tool("graph_upsert_tool")
def upsert_graph_relationship(source: str, relationship: str, target: str, detail: str = ""):
    """
    Saves a technical relationship to the Neo4j Knowledge Graph.
    Use this whenever you discover a connection between two concepts.
    Args:
        source: The starting entity (e.g., 'FastAPI').
        relationship: The action or link (e.g., 'uses', 'implements').
        target: The destination entity (e.g., 'Uvicorn').
        detail: Brief context about this specific connection.
    """
    try:
        neo4j_manager.upsert_relationship(
            source_node=source,
            relationship=relationship,
            target_node=target,
            properties={"detail": detail, "source_agent": "Astra_Researcher"}
        )
        return f"Successfully mapped: ({source})-[:{relationship}]->({target})"
    except Exception as e:
        return f"Failed to update graph: {str(e)}"

@tool("retrieve_knowledge")
def retrieve_knowledge(query: str):
    """
    Use this tool to search the knowledge graph for existing information. Input should be a simple string query.
    """
    try:
        results, reasoning = neo4j_manager.vector_search(query)
        if not results:
            return f"No existing knowledge found.\n{reasoning}"
        
        knowledge_string = "\n".join(results)
        return f"Existing Knowledge Found:\n{knowledge_string}\n\n{reasoning}"
    except Exception as e:
        return f"Tool Error: {str(e)}"