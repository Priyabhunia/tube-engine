const API_BASE = '/api';

let currentFilters = {
    query: '',
    content_type: '',
    agent_type: '',
    source_platform: '',
    sort_by: 'relevance',
    page: 1,
    page_size: 20
};

const typeIcons = {
    document: '📄',
    video: '🎬',
    post: '💬',
    code: '💻',
    artwork: '🎨',
    music: '🎵',
    research: '🔬',
    conversation: '💭',
    dataset: '📊',
    simulation: '🌐'
};

const typeColors = {
    document: '#00ff88',
    video: '#ff6b35',
    post: '#00d4ff',
    code: '#ffaa00',
    artwork: '#ff4466',
    music: '#aa66ff',
    research: '#00aaff',
    conversation: '#66ffaa',
    dataset: '#ff6688',
    simulation: '#88aaff'
};

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    setupEventListeners();
    await loadFilters();
    await loadStats();
    await loadRecentContent();
}

function setupEventListeners() {
    document.getElementById('searchForm').addEventListener('submit', handleSearch);
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSearch(e);
        }
    });

    document.querySelectorAll('.quick-filters .filter-btn').forEach(btn => {
        btn.addEventListener('click', handleQuickFilter);
    });

    document.getElementById('platformFilter').addEventListener('change', handleFilterChange);
    document.getElementById('agentTypeFilter').addEventListener('change', handleFilterChange);
    document.getElementById('sortByFilter').addEventListener('change', handleFilterChange);

    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('contentModal').addEventListener('click', (e) => {
        if (e.target.id === 'contentModal') closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

async function loadFilters() {
    try {
        const [platforms, agentTypes] = await Promise.all([
            fetch(`${API_BASE}/platforms`).then(r => r.json()),
            fetch(`${API_BASE}/agent-types`).then(r => r.json())
        ]);

        populateSelect('platformFilter', platforms, 'All Platforms');
        populateSelect('agentTypeFilter', agentTypes, 'All Agent Types');
    } catch (error) {
        console.error('Error loading filters:', error);
    }
}

async function loadStats() {
    try {
        const stats = await fetch(`${API_BASE}/stats`).then(r => r.json());
        
        document.getElementById('statAgents').textContent = formatNumber(stats.total_agents);
        document.getElementById('statContents').textContent = formatNumber(stats.total_contents);
        document.getElementById('statVideos').textContent = formatNumber(stats.total_videos);
        document.getElementById('statCode').textContent = formatNumber(stats.total_code);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadRecentContent() {
    try {
        const results = await fetch(`${API_BASE}/recent?limit=12`).then(r => r.json());
        displayResults(results, 'Recent Agent Creations');
    } catch (error) {
        console.error('Error loading recent content:', error);
        showError();
    }
}

function populateSelect(selectId, options, defaultLabel) {
    const select = document.getElementById(selectId);
    select.innerHTML = `<option value="">${defaultLabel}</option>`;
    options.forEach(option => {
        select.innerHTML += `<option value="${option}">${option}</option>`;
    });
}

function handleSearch(e) {
    e.preventDefault();
    currentFilters.query = document.getElementById('searchInput').value.trim();
    currentFilters.page = 1;
    performSearch();
}

function handleQuickFilter(e) {
    document.querySelectorAll('.quick-filters .filter-btn').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');

    currentFilters.content_type = e.target.dataset.type || '';
    currentFilters.page = 1;
    
    if (currentFilters.query) {
        performSearch();
    }
}

function handleFilterChange() {
    currentFilters.source_platform = document.getElementById('platformFilter').value;
    currentFilters.agent_type = document.getElementById('agentTypeFilter').value;
    currentFilters.sort_by = document.getElementById('sortByFilter').value;
    currentFilters.page = 1;
    
    if (currentFilters.query) {
        performSearch();
    }
}

async function performSearch() {
    if (!currentFilters.query) return;

    showLoading();

    try {
        const params = new URLSearchParams();
        params.append('query', currentFilters.query);
        if (currentFilters.content_type) params.append('content_type', currentFilters.content_type);
        if (currentFilters.agent_type) params.append('agent_type', currentFilters.agent_type);
        if (currentFilters.source_platform) params.append('source_platform', currentFilters.source_platform);
        params.append('sort_by', currentFilters.sort_by);
        params.append('page', currentFilters.page);
        params.append('page_size', currentFilters.page_size);

        const response = await fetch(`${API_BASE}/search?${params}`);
        const data = await response.json();

        displayResults(data.results, 'Search Results', data.total);
        displayPagination(data);
        
        document.getElementById('filtersSection').style.display = 'block';
        document.getElementById('resultsHeader').style.display = 'flex';
        document.getElementById('resultsCount').textContent = `${data.total} result${data.total !== 1 ? 's' : ''} for "${currentFilters.query}"`;
    } catch (error) {
        console.error('Search error:', error);
        showError();
    }
}

function showLoading() {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = `
        <div class="loading-placeholder">
            <div class="spinner"></div>
            <p>Searching agent creations...</p>
        </div>
    `;
}

function showError() {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = `
        <div class="loading-placeholder">
            <p>An error occurred. Please try again.</p>
        </div>
    `;
}

function displayResults(results, title = 'Results', total = null) {
    const grid = document.getElementById('resultsGrid');

    if (results.length === 0) {
        grid.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">🔍</div>
                <h3>No creations found</h3>
                <p>Try different search terms or filters</p>
            </div>
        `;
        document.getElementById('pagination').innerHTML = '';
        return;
    }

    grid.innerHTML = results.map(item => createContentCard(item)).join('');

    document.querySelectorAll('.content-card').forEach(card => {
        card.addEventListener('click', () => {
            const contentId = card.dataset.id;
            openContentModal(contentId);
        });
    });
}

function createContentCard(item) {
    const icon = typeIcons[item.content_type] || '📄';
    const color = typeColors[item.content_type] || '#00ff88';
    const tags = item.tags?.slice(0, 3) || [];
    const agent = item.agent;
    const agentInitial = agent?.name?.charAt(0).toUpperCase() || '?';

    return `
        <div class="content-card" data-id="${item.id}">
            <div class="card-thumbnail">
                <span class="type-icon">${icon}</span>
                <span class="content-type-badge" style="color: ${color}">${item.content_type}</span>
            </div>
            <div class="card-body">
                <h3 class="card-title">${escapeHtml(item.title)}</h3>
                <p class="card-description">${escapeHtml(item.description || 'No description available')}</p>
                <div class="card-agent">
                    <div class="agent-avatar" style="background: linear-gradient(135deg, ${color} 0%, ${adjustColor(color, -30)} 100%)">${agentInitial}</div>
                    <div class="agent-info">
                        <div class="agent-name">${agent?.display_name || agent?.name || 'Unknown Agent'}</div>
                        <div class="agent-type">${agent?.agent_type || 'Agent'}</div>
                    </div>
                </div>
                <div class="card-stats">
                    <span class="stat-item">👁 ${formatNumber(item.view_count)}</span>
                    <span class="stat-item">❤️ ${formatNumber(item.like_count)}</span>
                    <span class="stat-item">🔗 ${formatNumber(item.share_count)}</span>
                </div>
                ${tags.length > 0 ? `
                    <div class="card-tags">
                        ${tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function displayPagination(data) {
    const pagination = document.getElementById('pagination');
    const totalPages = data.total_pages;

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    html += `<button class="page-btn" ${data.page === 1 ? 'disabled' : ''} data-page="${data.page - 1}">← Prev</button>`;

    const startPage = Math.max(1, data.page - 2);
    const endPage = Math.min(totalPages, data.page + 2);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === data.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    html += `<button class="page-btn" ${data.page === totalPages ? 'disabled' : ''} data-page="${data.page + 1}">Next →</button>`;

    pagination.innerHTML = html;

    pagination.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = parseInt(btn.dataset.page);
            if (page && page !== currentFilters.page) {
                currentFilters.page = page;
                performSearch();
                window.scrollTo({ top: 300, behavior: 'smooth' });
            }
        });
    });
}

async function openContentModal(contentId) {
    try {
        const response = await fetch(`${API_BASE}/content/${contentId}`);
        const item = await response.json();

        const modal = document.getElementById('contentModal');
        const modalBody = document.getElementById('modalBody');

        const icon = typeIcons[item.content_type] || '📄';
        const color = typeColors[item.content_type] || '#00ff88';
        const agent = item.agent;
        const agentInitial = agent?.name?.charAt(0).toUpperCase() || '?';
        const tags = item.tags || [];

        modalBody.innerHTML = `
            <div class="modal-header">
                <span class="modal-type" style="background: ${color}">${item.content_type}</span>
                <h2 class="modal-title">${escapeHtml(item.title)}</h2>
            </div>

            <div class="modal-agent-section">
                <div class="modal-agent-avatar" style="background: linear-gradient(135deg, ${color} 0%, ${adjustColor(color, -30)} 100%)">${agentInitial}</div>
                <div class="modal-agent-details">
                    <h4>${agent?.display_name || agent?.name || 'Unknown Agent'}</h4>
                    <p>${agent?.bio || agent?.agent_type || 'Autonomous AI Agent'}</p>
                </div>
            </div>

            <div class="modal-section">
                <h3 class="modal-section-title">Description</h3>
                <p class="modal-description">${escapeHtml(item.description || 'No description available.')}</p>
            </div>

            <div class="modal-section">
                <h3 class="modal-section-title">Statistics</h3>
                <div class="modal-stats">
                    <div class="modal-stat">
                        <div class="modal-stat-value">${formatNumber(item.view_count)}</div>
                        <div class="modal-stat-label">Views</div>
                    </div>
                    <div class="modal-stat">
                        <div class="modal-stat-value">${formatNumber(item.like_count)}</div>
                        <div class="modal-stat-label">Likes</div>
                    </div>
                    <div class="modal-stat">
                        <div class="modal-stat-value">${formatNumber(item.share_count)}</div>
                        <div class="modal-stat-label">Shares</div>
                    </div>
                    <div class="modal-stat">
                        <div class="modal-stat-value">${formatNumber(item.download_count)}</div>
                        <div class="modal-stat-label">Downloads</div>
                    </div>
                </div>
            </div>

            ${tags.length > 0 ? `
                <div class="modal-section">
                    <h3 class="modal-section-title">Tags</h3>
                    <div class="modal-tags">
                        ${tags.map(tag => `<span class="modal-tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                </div>
            ` : ''}

            <div class="modal-section">
                <h3 class="modal-section-title">Details</h3>
                <div class="modal-meta">
                    <div class="modal-meta-item">
                        <span class="modal-meta-label">Platform</span>
                        <span class="modal-meta-value">${item.source_platform || 'Unknown'}</span>
                    </div>
                    <div class="modal-meta-item">
                        <span class="modal-meta-label">Language</span>
                        <span class="modal-meta-value">${item.language || 'N/A'}</span>
                    </div>
                    <div class="modal-meta-item">
                        <span class="modal-meta-label">License</span>
                        <span class="modal-meta-value">${item.license || 'Unknown'}</span>
                    </div>
                    <div class="modal-meta-item">
                        <span class="modal-meta-label">Indexed</span>
                        <span class="modal-meta-value">${formatDate(item.indexed_at)}</span>
                    </div>
                </div>
            </div>

            <div class="modal-actions">
                ${item.content_url ? `<a href="${escapeHtml(item.content_url)}" target="_blank" rel="noopener" class="btn btn-primary">View Content</a>` : ''}
                ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener" class="btn btn-secondary">View Source</a>` : ''}
            </div>
        `;

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    } catch (error) {
        console.error('Error loading content:', error);
    }
}

function closeModal() {
    const modal = document.getElementById('contentModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function adjustColor(color, amount) {
    const hex = color.replace('#', '');
    const num = parseInt(hex, 16);
    const r = Math.min(255, Math.max(0, (num >> 16) + amount));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amount));
    const b = Math.min(255, Math.max(0, (num & 0x0000FF) + amount));
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}