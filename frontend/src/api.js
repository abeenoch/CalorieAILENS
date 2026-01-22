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

    scanBarcode: (barcode, context, notes) =>
        apiCall(`/analyze/barcode?barcode=${encodeURIComponent(barcode)}&context=${encodeURIComponent(context || '')}&notes=${encodeURIComponent(notes || '')}`, {
            method: 'POST',
        }),

    getHistory: (limit = 20, offset = 0, filters = {}) => {
        const params = new URLSearchParams({
            limit,
            offset,
            ...(filters.startDate && { start_date: filters.startDate }),
            ...(filters.endDate && { end_date: filters.endDate }),
            ...(filters.context && { context: filters.context }),
            ...(filters.foodName && { food_name: filters.foodName }),
        });
        return apiCall(`/analyze/history?${params.toString()}`);
    },

    getMealDetail: (mealId) =>
        apiCall(`/analyze/meal/${mealId}`),

    getTodayMacros: () =>
        apiCall('/analyze/macros/today'),

    getMacrosByDateRange: (startDate, endDate) =>
        apiCall(`/analyze/macros/date-range?start_date=${startDate}&end_date=${endDate}`),
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

// Notifications API
export const notificationsAPI = {
    getPreferences: () =>
        apiCall('/notifications/preferences'),

    updatePreferences: (preferences) =>
        apiCall('/notifications/preferences', {
            method: 'PUT',
            body: JSON.stringify(preferences),
        }),

    checkMealReminder: () =>
        apiCall('/notifications/check-meal-reminder'),
};

// Exports API
export const exportsAPI = {
    getWeeklySummary: () =>
        apiCall('/exports/weekly-summary'),

    createShareableWeeklySummary: () =>
        apiCall('/exports/weekly-summary/share', {
            method: 'POST',
        }),

    getSharedSummary: (shareToken) =>
        apiCall(`/exports/shared/${shareToken}`),
};

// Balance API
export const balanceAPI = {
    getToday: () => apiCall('/balance/today'),

    getWeek: () => apiCall('/balance/week'),
};

export { apiCall, API_BASE_URL };
