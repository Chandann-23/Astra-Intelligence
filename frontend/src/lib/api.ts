import axios from 'axios';

// 1. Define the URL from env or fallback
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "https://astra-intelligence-production.up.railway.app";

// 2. Create the axios instance using the variable we just defined
const api = axios.create({
  baseURL: BACKEND_URL,
});

// 3. Export everything correctly
export default api;
export { BACKEND_URL };