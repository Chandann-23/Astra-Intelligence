import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://astra-intelligence-production.up.railway.app";';

const api = axios.create({
  baseURL: BACKEND_URL,
});

export default api;
export { BACKEND_URL };
