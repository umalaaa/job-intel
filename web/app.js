class JobIntelligenceApp {
  constructor() {
    this.currentLang = 'en';
    this.translations = {};
    this.summaryData = null;
    this.rolesData = null;
    this.filteredRoles = null;
    this.innovationsData = null;
    this.rareJobsData = null;
    this.searchQuery = '';
    this.isLoading = true;

    this.translations = {
      en: {
        logo: 'Job Intelligence',
        heroTitle: 'Talent Market Intelligence',
        heroSubtitle: 'Weekly pulse on roles, skills, and hiring momentum across Canada',
        totalPostings: 'Open Roles',
        growthRate: 'YoY Momentum',
        regionalOverview: 'Region Snapshot',
        latestRoles: 'Fresh Opportunities',
        role: 'Role',
        company: 'Company',
        location: 'Location',
        salary: 'Comp',
        trend: 'Trend',
        skills: 'Core Skills',
        source: 'Source',
        trendingSkills: 'Skills on the Rise',
        marketInsights: 'Market Signals',
        innovationDemand: 'Innovation Demand',
        topCategories: 'Top Focus Areas',
        innovationRoles: 'Innovation Roles',
        footerText: 'Job Intelligence Dashboard © 2026. Updated',
        trendUp: 'Accelerating',
        trendDown: 'Cooling',
        trendStable: 'Steady'
      },
      zh: {
        logo: '就业情报',
        heroTitle: '人才市场情报',
        heroSubtitle: '每周追踪加拿大岗位、技能与招聘动向',
        totalPostings: '开放岗位',
        growthRate: '年同比动能',
        regionalOverview: '区域速览',
        latestRoles: '最新机会',
        role: '职位',
        company: '公司',
        location: '地点',
        salary: '薪酬',
        trend: '趋势',
        skills: '核心技能',
        source: '来源',
        trendingSkills: '技能走强',
        marketInsights: '市场信号',
        innovationDemand: '创新需求',
        topCategories: '关注领域',
        innovationRoles: '创新岗位',
        footerText: '就业情报仪表板 © 2026. 更新于',
        trendUp: '加速',
        trendDown: '降温',
        trendStable: '平稳'
      }
    };

    this.init();
  }

  setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
    
    // In dev mode or separate frontend, might need config
    // If files served by FastAPI, relative path works.
    // If served by file://, WS won't work easily without hardcoded URL.
    // Assume served by FastAPI or same origin.
    
    try {
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'jobs_updated') {
                    this.showNotification(`New jobs from ${data.source}: ${data.count}`);
                    this.fetchRoles(); 
                    this.fetchSummary();
                }
            } catch (e) {
                console.error('WS message error', e);
            }
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected, retrying in 5s...');
            setTimeout(() => this.setupWebSocket(), 5000);
        };
    } catch (e) {
        console.warn('WebSocket setup failed', e);
    }
  }

  showNotification(message) {
    const note = document.createElement('div');
    note.className = 'notification-toast';
    note.textContent = message;
    document.body.appendChild(note);
    
    setTimeout(() => {
        note.classList.add('show');
        setTimeout(() => {
            note.classList.remove('show');
            setTimeout(() => note.remove(), 300);
        }, 3000);
    }, 10);
  }

  async init() {
    this.setupWebSocket();
    this.showLoading();
    try {
      await Promise.all([
        this.fetchSummary(),
        this.fetchRoles(),
        this.fetchInnovations(),
        this.fetchRareJobs()
      ]);

      this.filteredRoles = [...this.rolesData];
      this.isLoading = false;
      this.hideLoading();
      this.render();
      this.setupEventListeners();
      this.animateOnScroll();
    } catch (error) {
      console.error('Error initializing app:', error);
      this.hideLoading();
      this.showError();
    }
  }

  showLoading() {
    const loader = document.createElement('div');
    loader.id = 'appLoader';
    loader.innerHTML = `
      <div class="loader-content">
        <div class="loader-spinner"></div>
        <p class="loader-text">Loading intelligence data...</p>
      </div>
    `;
    loader.style.cssText = `
      position: fixed;
      inset: 0;
      background: var(--color-bg);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    `;
    document.body.appendChild(loader);
  }

  hideLoading() {
    const loader = document.getElementById('appLoader');
    if (loader) {
      loader.style.opacity = '0';
      loader.style.transition = 'opacity 0.5s ease';
      setTimeout(() => loader.remove(), 500);
    }
  }

  animateOnScroll() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.metric-card, .region-card, .skill-item, .insight-card, .category-item, .innovation-role-card, .rare-job-card, .weird-job-card').forEach(el => {
      observer.observe(el);
    });
  }

  async fetchSummary() {
    const response = await fetch('data/summary.json');
    if (!response.ok) throw new Error('Failed to fetch summary data');
    this.summaryData = await response.json();
  }

  async fetchRoles() {
    const response = await fetch('data/roles.json');
    if (!response.ok) throw new Error('Failed to fetch roles data');
    this.rolesData = await response.json();
  }

  async fetchInnovations() {
    const response = await fetch('data/innovations.json');
    if (!response.ok) throw new Error('Failed to fetch innovations data');
    this.innovationsData = await response.json();
  }

  async fetchRareJobs() {
    const response = await fetch('data/rare_jobs.json');
    if (!response.ok) throw new Error('Failed to fetch rare jobs data');
    this.rareJobsData = await response.json();
  }

  render() {
    this.renderHero();
    this.renderMetrics();
    this.renderRegions();
    this.renderRolesTable();
    this.renderSkills();
    this.renderCategories();
    this.renderInnovationRoles();
    this.renderInsights();
    this.renderRareJobs();
    this.renderDates();
  }

  renderHero() {
    const title = document.querySelector('.hero-title');
    const subtitle = document.querySelector('.hero-subtitle');

    title.textContent = this.summaryData.title[this.currentLang];
    subtitle.textContent = this.translations[this.currentLang].heroSubtitle;
  }

  renderMetrics() {
    const totalPostingsEl = document.getElementById('totalPostings');
    const growthRateEl = document.getElementById('growthRate');

    totalPostingsEl.textContent = this.formatNumber(this.summaryData.totalPostings);
    growthRateEl.textContent = this.summaryData.growthRate.toFixed(1);
  }

  renderRegions() {
    const grid = document.getElementById('regionsGrid');
    grid.innerHTML = '';

    this.summaryData.regions.forEach((region, index) => {
      const card = document.createElement('div');
      card.className = 'region-card';
      card.style.animationDelay = `${index * 0.1}s`;

      const avgSalary = this.calculateAverageSalary();
      const count = Math.floor(this.summaryData.totalPostings / this.summaryData.regions.length);

      card.innerHTML = `
        <div class="region-name">${region}</div>
        <div class="region-stats">
          <span>${this.formatNumber(count)} ${this.translations[this.currentLang].totalPostings}</span>
        </div>
      `;

      grid.appendChild(card);
    });
  }

  renderRolesTable() {
    const tbody = document.getElementById('rolesTableBody');
    tbody.innerHTML = '';

    const rolesToRender = this.filteredRoles || this.rolesData;

    if (!rolesToRender.length) {
      const row = document.createElement('tr');
      row.innerHTML = `<td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-text-secondary);">
        ${this.currentLang === 'en' ? 'No matching roles found' : '未找到匹配职位'}
      </td>`;
      tbody.appendChild(row);
      return;
    }

    rolesToRender.forEach((role, index) => {
      const row = document.createElement('tr');
      row.style.animationDelay = `${index * 0.05}s`;

      const trendClass = `trend-${role.trend}`;
      const trendText = this.getTrendText(role.trend);
      const trendIcon = this.getTrendIcon(role.trend);

      const roleLink = role.url
        ? `<a href="${role.url}" target="_blank" rel="noopener noreferrer" class="role-link">${role.role}</a>`
        : role.role;

      const sourceBadge = role.source
        ? `<span class="source-badge">${role.source}</span>`
        : '-';

      row.innerHTML = `
        <td>
          <div class="role-name">${roleLink}</div>
          <div class="role-company">${role.company}</div>
        </td>
        <td>${role.company}</td>
        <td>${role.location}</td>
        <td>${role.salary}</td>
        <td>
          <span class="trend-badge ${trendClass}">
            ${trendIcon} ${trendText}
          </span>
        </td>
        <td>
          <div class="skills-tags">
            ${role.skills.slice(0, 3).map(skill =>
              `<span class="skill-tag">${skill}</span>`
            ).join('')}
            ${role.skills.length > 3 ? `<span class="skill-tag">+${role.skills.length - 3}</span>` : ''}
          </div>
        </td>
        <td>${sourceBadge}</td>
      `;

      tbody.appendChild(row);
    });
  }

  renderSkills() {
    const list = document.getElementById('skillsList');
    list.innerHTML = '';

    const maxCount = Math.max(...this.summaryData.topSkills.map(s => s.count));

    this.summaryData.topSkills.forEach((skill, index) => {
      const item = document.createElement('div');
      item.className = 'skill-item';
      item.style.animationDelay = `${index * 0.1}s`;

      const percentage = (skill.count / maxCount) * 100;
      const changeClass = skill.change >= 0 ? 'positive' : 'negative';
      const changeSign = skill.change >= 0 ? '+' : '';

      item.innerHTML = `
        <div class="skill-header">
          <span class="skill-name">${skill.name}</span>
          <span class="skill-change ${changeClass}">
            ${changeSign}${skill.change.toFixed(1)}%
          </span>
        </div>
        <div class="skill-bar-bg">
          <div class="skill-bar-fill" style="width: 0%" data-width="${percentage}%"></div>
        </div>
      `;

      list.appendChild(item);
    });

    setTimeout(() => {
      document.querySelectorAll('.skill-bar-fill').forEach(bar => {
        bar.style.width = bar.dataset.width;
      });
    }, 300);
  }

  renderInsights() {
    const grid = document.getElementById('insightsGrid');
    grid.innerHTML = '';

    this.summaryData.insights.forEach((insight, index) => {
      const card = document.createElement('div');
      card.className = 'insight-card';
      card.style.animationDelay = `${index * 0.1}s`;

      card.innerHTML = `
        <div class="insight-icon">${insight.icon}</div>
        <h3 class="insight-title">${insight.title[this.currentLang]}</h3>
        <p class="insight-description">${insight.description[this.currentLang]}</p>
      `;

      grid.appendChild(card);
    });
  }

  renderCategories() {
    const list = document.getElementById('categoriesList');
    list.innerHTML = '';

    if (!this.innovationsData || !this.innovationsData.categories.length) {
      list.textContent = this.currentLang === 'en' ? 'No innovation data yet.' : '暂无创新数据。';
      return;
    }

    const maxCount = Math.max(...this.innovationsData.categories.map(c => c.count));

    this.innovationsData.categories.forEach((category, index) => {
      const item = document.createElement('div');
      item.className = 'category-item';
      item.style.animationDelay = `${index * 0.1}s`;

      const percentage = (category.count / maxCount) * 100;

      item.innerHTML = `
        <div class="category-header">
          <span class="category-name">${category.name}</span>
          <span class="category-count">${this.formatNumber(category.count)}</span>
        </div>
        <div class="category-bar-bg">
          <div class="category-bar-fill" style="width: 0%" data-width="${percentage}%"></div>
        </div>
      `;

      list.appendChild(item);
    });

    setTimeout(() => {
      document.querySelectorAll('.category-bar-fill').forEach(bar => {
        bar.style.width = bar.dataset.width;
      });
    }, 300);
  }

  renderInnovationRoles() {
    const list = document.getElementById('innovationRolesList');
    list.innerHTML = '';

    if (!this.innovationsData || !this.innovationsData.topRoles.length) {
      list.textContent = this.currentLang === 'en' ? 'No innovation roles found.' : '暂无创新职位。';
      return;
    }

    this.innovationsData.topRoles.forEach((role, index) => {
      const card = document.createElement('div');
      card.className = 'innovation-role-card';
      card.style.animationDelay = `${index * 0.1}s`;

      const roleLink = role.url
        ? `<a href="${role.url}" target="_blank" rel="noopener noreferrer" class="role-link">${role.role}</a>`
        : role.role;

      card.innerHTML = `
        <div class="inn-role-header">
          <div class="inn-role-info">
            <div class="inn-role-name">${roleLink}</div>
            <div class="inn-role-company">${role.company}</div>
          </div>
          <div class="inn-role-salary">${role.salary}</div>
        </div>
        <div class="inn-role-meta">
          <span class="inn-role-location">${role.location}</span>
        </div>
        <div class="inn-innovations">
          ${role.innovations.map(innovation =>
            `<span class="inn-innovation-tag">${innovation}</span>`
          ).join('')}
        </div>
      `;

      list.appendChild(card);
    });
  }

  renderRareJobs() {
    const rareList = document.getElementById('rareJobsList');
    const weirdList = document.getElementById('weirdJobsList');

    rareList.innerHTML = '';
    weirdList.innerHTML = '';

    if (!this.rareJobsData) {
      const message = this.currentLang === 'en' ? 'Rare roles will appear soon.' : '稀有职位即将发布。';
      rareList.textContent = message;
      weirdList.textContent = message;
      return;
    }

    const rareRoles = this.rareJobsData.rareRoles || [];
    const weirdRoles = this.rareJobsData.weirdRoles || [];

    if (!rareRoles.length) {
      rareList.textContent = this.currentLang === 'en' ? 'No rare jobs yet.' : '暂无稀有职位。';
    } else {
      rareRoles.forEach((role, index) => {
        const card = document.createElement('article');
        card.className = 'rare-job-card';
        card.style.animationDelay = `${index * 0.08}s`;
        card.innerHTML = this.buildRareWeirdCard(role);
        rareList.appendChild(card);
      });
    }

    if (!weirdRoles.length) {
      weirdList.textContent = this.currentLang === 'en' ? 'No weird jobs yet.' : '暂无怪奇职位。';
    } else {
      weirdRoles.forEach((role, index) => {
        const card = document.createElement('article');
        card.className = 'weird-job-card';
        card.style.animationDelay = `${index * 0.08}s`;
        card.innerHTML = this.buildRareWeirdCard(role, true);
        weirdList.appendChild(card);
      });
    }
  }

  buildRareWeirdCard(role, isWeird = false) {
    const roleLink = role.url
      ? `<a href="${role.url}" target="_blank" rel="noopener noreferrer" class="role-link">${role.role}</a>`
      : role.role;

    const tags = (isWeird && role.weirdTags && role.weirdTags.length)
      ? role.weirdTags
      : role.skills || [];

    const tagMarkup = tags.length
      ? tags.map(tag => `<span class="rare-tag">${tag}</span>`).join('')
      : `<span class="rare-tag empty">${this.currentLang === 'en' ? 'No tags' : '暂无标签'}</span>`;

    const sourceMarkup = role.source
      ? `<span class="rare-source">${role.source}</span>`
      : '';

    return `
      <div class="rare-card-header">
        <div class="rare-card-title">${roleLink}</div>
        <div class="rare-card-salary">${role.salary}</div>
      </div>
      <div class="rare-card-meta">
        <span class="rare-card-company">${role.company}</span>
        <span class="rare-card-location">${role.location}</span>
      </div>
      <div class="rare-card-tags">
        ${tagMarkup}
      </div>
      <div class="rare-card-footer">
        ${sourceMarkup}
      </div>
    `;
  }

  renderDates() {
    const dateStr = this.formatDate(this.summaryData.updatedAt);

    const heroDateEl = document.getElementById('heroDate');
    const footerDateEl = document.getElementById('footerDate');

    heroDateEl.textContent = dateStr;
    footerDateEl.textContent = dateStr;
  }

  updateLanguage(lang) {
    this.currentLang = lang;

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      if (this.translations[lang][key]) {
        el.textContent = this.translations[lang][key];
      }
    });

    document.querySelector('.lang-current').textContent = lang.toUpperCase();
    document.querySelector('.lang-alt').textContent = lang === 'en' ? '中文' : 'EN';

    this.renderHero();
    this.renderRegions();
    this.renderRolesTable();
    this.renderInsights();
    this.renderRareJobs();
  }

  setupEventListeners() {
    const langToggle = document.getElementById('langToggle');
    langToggle.addEventListener('click', () => {
      const newLang = this.currentLang === 'en' ? 'zh' : 'en';
      this.updateLanguage(newLang);
    });

    const searchInput = document.getElementById('roleSearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.filterRoles();
      });
    }
  }

  filterRoles() {
    if (!this.searchQuery) {
      this.filteredRoles = [...this.rolesData];
    } else {
      this.filteredRoles = this.rolesData.filter(role => {
        const searchable = `${role.role} ${role.company} ${role.location} ${(role.skills || []).join(' ')}`.toLowerCase();
        return searchable.includes(this.searchQuery);
      });
    }
    this.renderRolesTable();
  }

  formatNumber(num) {
    return num.toLocaleString('en-US');
  }

  formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString(this.currentLang === 'en' ? 'en-US' : 'zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  calculateAverageSalary() {
    return 0;
  }

  getTrendText(trend) {
    const key = `trend${trend.charAt(0).toUpperCase() + trend.slice(1)}`;
    return this.translations[this.currentLang][key] || trend;
  }

  getTrendIcon(trend) {
    switch (trend) {
      case 'up': return '↑';
      case 'down': return '↓';
      case 'stable': return '→';
      default: return '•';
    }
  }

  showError() {
    document.querySelector('.main').innerHTML = `
      <div style="text-align: center; padding: 4rem;">
        <h2 style="color: var(--color-danger); margin-bottom: 1rem;">Error Loading Data</h2>
        <p style="color: var(--color-text-secondary);">Please ensure data files are present and try again.</p>
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new JobIntelligenceApp();
});
