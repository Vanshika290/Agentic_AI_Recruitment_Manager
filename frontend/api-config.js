const LOCAL_API_BASE = 'http://localhost:8000';
const DEPLOYED_API_BASE = 'https://agentic-airecruitmentmanager-production.up.railway.app';

const isLocalDevelopment = ['localhost', '127.0.0.1'].includes(window.location.hostname);
window.RECRUITMENT_API_BASE =
  (window.RECRUITMENT_API_BASE || (isLocalDevelopment ? LOCAL_API_BASE : DEPLOYED_API_BASE))
    .replace(/\/+$/, '');
