// Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.1.0
// Admin Authentication & Security Management

const TOKEN_KEY = 'myagent_access_token';
const USER_KEY = 'myagent_user';

function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getAuthHeaders() {
  const token = getAuthToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function checkAuthentication() {
  const token = getAuthToken();
  const loginOverlay = document.getElementById('login-overlay');
  const userBadge = document.getElementById('logged-in-user-name');

  if (!token) {
    if (loginOverlay) loginOverlay.style.display = 'flex';
    return false;
  }

  if (userBadge) {
    userBadge.innerText = localStorage.getItem(USER_KEY) || 'admin';
  }
  if (loginOverlay) loginOverlay.style.display = 'none';
  return true;
}

async function performLogin(event) {
  if (event) event.preventDefault();

  const userField = document.getElementById('login-username');
  const passField = document.getElementById('login-password');
  const errBox = document.getElementById('login-error-msg');
  const loginBtn = document.getElementById('btn-do-login');

  const username = userField.value.trim();
  const password = passField.value.trim();

  if (!username || !password) {
    errBox.style.display = 'block';
    errBox.innerText = 'অনুগ্রহ করে ইউজারনেম এবং পাসওয়ার্ড দিন।';
    return;
  }

  loginBtn.disabled = true;
  loginBtn.innerText = 'লগইন হচ্ছে...';
  errBox.style.display = 'none';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (res.ok && data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, data.username);
      
      const loginOverlay = document.getElementById('login-overlay');
      if (loginOverlay) loginOverlay.style.display = 'none';
      
      const userBadge = document.getElementById('logged-in-user-name');
      if (userBadge) userBadge.innerText = data.username;

      showToast(`স্বাগতম ${data.username}! সফলভাবে লগইন হয়েছে।`, 'success');
      
      // Initialize sessions and documents
      if (typeof loadChatSessions === 'function') loadChatSessions();
      if (typeof loadDocumentList === 'function') loadDocumentList();
      if (typeof loadMemoryStats === 'function') loadMemoryStats();
    } else {
      errBox.style.display = 'block';
      errBox.innerText = data.detail || 'ভুল ইউজারনেম বা পাসওয়ার্ড!';
    }
  } catch (err) {
    errBox.style.display = 'block';
    errBox.innerText = `সার্ভার সংযোগ ত্রুটি: ${err.message}`;
  } finally {
    loginBtn.disabled = false;
    loginBtn.innerText = 'লগইন করুন';
  }
}

function logout() {
  if (!confirm('আপনি কি নিশ্চিত যে লগআউট করতে চান?')) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  const loginOverlay = document.getElementById('login-overlay');
  if (loginOverlay) loginOverlay.style.display = 'flex';
  showToast('সফলভাবে লগআউট হয়েছে।', 'info');
}

document.addEventListener('DOMContentLoaded', () => {
  checkAuthentication();
});
