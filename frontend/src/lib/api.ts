import axios from 'axios';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
});

export default api;
export { BACKEND_URL };
