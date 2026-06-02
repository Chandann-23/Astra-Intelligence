from langchain.tools import tool
from neo4j import AsyncGraphDatabase
import os
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

class AsyncNeo4jManager:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "neo4j+s://localhost:7687")
        self.user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
        self.password = os.getenv("NEO4J_PASSWORD", "password123")
        self._driver = None
        self._index_initialized = False
        
        print("Loading local SentenceTransformer model (Zero-latency embeddings)...")
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            print("Local embeddings ready.")
        except Exception as e:
            print(f"Failed to load embedder: {e}")
            self.embedder = None
            
        print("AsyncNeo4jManager initialized.")

    @property
    def driver(self):
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            except Exception as e:
                print(f"CRITICAL: Could not initialize Neo4j driver for {self.uri}: {e}")
        return self._driver

    def get_embedding(self, text):
        if not self.embedder:
            return [0.0] * 384
        try:
            embeddings = self.embedder.encode([text])
            return embeddings[0].tolist()
        except Exception as e:
            print(f"Embedding Request Failed: {e}")
            return [0.0] * 384

    async def ensure_index(self):
        if not self._index_initialized and self.driver:
            try:
                await self.create_vector_index()
                if await self.verify_index():
                    print("SUCCESS: Vector Index 'concept_embeddings' is ONLINE.")
                    self._index_initialized = True
            except Exception as e:
                print(f"WARNING: Index initialization deferred: {e}")

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def create_vector_index(self):
        if not self.driver: return
        async with self.driver.session() as session:
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
                await session.run(query)
                print("Vector index initialization command sent.")
            except Exception as e:
                print(f"Index creation skipped/failed: {e}")

    async def verify_index(self):
        if not self.driver: return False
        async with self.driver.session() as session:
            query = "SHOW INDEXES YIELD name, type, state WHERE name = 'concept_embeddings'"
            result = await session.run(query)
            record = await result.single()
            if record and record['state'] == 'ONLINE':
                return True
            return False

    async def upsert_relationship(self, source_node: str, relationship: str, target_node: str, properties: dict = None):
        await self.ensure_index()
        if not self.driver: return
        
        source_embedding = self.get_embedding(source_node)
        target_embedding = self.get_embedding(target_node)
        
        clean_rel = "".join(e for e in relationship if e.isalnum() or e == '_').upper()
        
        async with self.driver.session() as session:
            query = (
                "MERGE (s:Concept {name: $source}) "
                "ON CREATE SET s.embedding = $source_emb "
                "MERGE (t:Concept {name: $target}) "
                "ON CREATE SET t.embedding = $target_emb "
                f"MERGE (s)-[r:{clean_rel}]->(t) "
                "SET r += $props "
                "RETURN s, r, t"
            )
            await session.run(
                query, 
                source=source_node, 
                source_emb=source_embedding,
                target=target_node, 
                target_emb=target_embedding,
                props=properties or {}
            )

    async def vector_search(self, query: str, top_k: int = 5):
        await self.ensure_index()
        if not self.driver: return [], "Database offline."
        
        query_embedding = self.get_embedding(query)
        
        async with self.driver.session() as session:
            search_query = """
            CALL db.index.vector.queryNodes('concept_embeddings', $k, $query_emb)
            YIELD node, score
            MATCH (node)-[r]-(neighbor:Concept)
            RETURN node.name as entity, type(r) as relationship, neighbor.name as connected_to, score
            ORDER BY score DESC
            LIMIT 15
            """
            result = await session.run(search_query, query_emb=query_embedding, k=top_k)
            records = await result.data()
            
            knowledge_bits = []
            top_score = 0
            best_match = ""
            
            for record in records:
                bit = f"[{record['entity']}] --({record['relationship']})--> [{record['connected_to']}]"
                if bit not in knowledge_bits:
                    knowledge_bits.append(bit)
                if record['score'] > top_score:
                    top_score = record['score']
                    best_match = record['entity']
            
            reasoning = f"Reasoning: Retrieved nodes based on semantic proximity to '{query}'. Best match found was '{best_match}' with a confidence score of {top_score:.2f}."
            
            return knowledge_bits, reasoning

    async def execute_query(self, query, parameters=None):
        if not self.driver: return []
        async with self.driver.session() as session:
            try:
                result = await session.run(query, parameters)
                return await result.data()
            except Exception as e:
                print(f"SRE Alert - Graph Write Failed: {e}")
                raise e

neo4j_manager = AsyncNeo4jManager()

@tool("graph_upsert_tool")
async def upsert_graph_relationship(source: str, relationship: str, target: str, detail: str = ""):
    """Saves a technical relationship to the Neo4j Knowledge Graph."""
    try:
        await neo4j_manager.upsert_relationship(
            source_node=source,
            relationship=relationship,
            target_node=target,
            properties={"detail": detail, "source_agent": "Astra_Researcher"}
        )
        return f"Successfully mapped: ({source})-[:{relationship}]->({target})"
    except Exception as e:
        return f"Failed to update graph: {str(e)}"

@tool("retrieve_knowledge")
async def retrieve_knowledge(query: str):
    """Use this tool to search the knowledge graph for existing information."""
    try:
        results, reasoning = await neo4j_manager.vector_search(query)
        if not results:
            return f"No existing knowledge found.\n{reasoning}"
        
        knowledge_string = "\n".join(results)
        return f"Existing Knowledge Found:\n{knowledge_string}\n\n{reasoning}"
    except Exception as e:
        return f"Tool Error: {str(e)}"