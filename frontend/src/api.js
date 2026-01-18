// API Configuration
// Use relative URLs so it works whether backend is on same server or different domain
const API_BASE_URL = typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : '';  // Empty string = use same origin (backend serves frontend)

// Helper for API calls
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }

    return response.json();
}

// Auth API
export const authAPI = {
    register: (email, password) =>
        apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        }),

    login: (email, password) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        return fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        }).then(async res => {
            if (!res.ok) {
                const error = await res.json().catch(() => ({ detail: 'Login failed' }));
                throw new Error(error.detail || 'Login failed');
            }
            return res.json();
        });
    },

    getMe: () => apiCall('/auth/me'),
};

// Profile API
export const profileAPI = {
    get: () => apiCall('/profile/'),

    update: (data) =>
        apiCall('/profile/', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getOptions: () => apiCall('/profile/options'),
};

// Analyze API
export const analyzeAPI = {
    analyzeMeal: (imageData, imageMimeType, context, notes) =>
        apiCall('/analyze/meal', {
            method: 'POST',
            body: JSON.stringify({
                image_data: imageData,
                image_mime_type: imageMimeType,
                context,
                notes,
            }),
        }),

    getHistory: (limit = 20, offset = 0) =>
        apiCall(`/analyze/history?limit=${limit}&offset=${offset}`),

    getMealDetail: (mealId) =>
        apiCall(`/analyze/meal/${mealId}`),
};

// Feedback API
export const feedbackAPI = {
    create: (mealId, feedbackType, comment) =>
        apiCall('/feedback/', {
            method: 'POST',
            body: JSON.stringify({
                meal_id: mealId,
                feedback_type: feedbackType,
                comment,
            }),
        }),

    getMealFeedback: (mealId) =>
        apiCall(`/feedback/meal/${mealId}`),

    getStats: () =>
        apiCall('/feedback/stats'),
};

// Balance API
export const balanceAPI = {
    getToday: () => apiCall('/balance/today'),

    getWeek: () => apiCall('/balance/week'),
};

export { apiCall, API_BASE_URL };
