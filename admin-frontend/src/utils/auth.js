const TOKEN_KEY = 'ciee_dashboard_token';


export function getDashboardToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setDashboardToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function removeDashboardToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}
