class JobIntelligenceApp {
  constructor() {
    this.currentLang = 'en';
    this.translations = {};
    this.summaryData = null;
    this.rolesData = null;

    this.translations = {
      en: {
        logo: 'Job Intelligence',
        heroTitle: 'Market Intelligence',
        heroSubtitle: 'Real-time insights on job trends, skills demand, and market dynamics',
        totalPostings: 'Active Postings',
        growthRate: 'YoY Growth',
        regionalOverview: 'Regional Overview',
        latestRoles: 'Latest Opportunities',
        role: 'Role',
        company: 'Company',
        location: 'Location',
        salary: 'Salary',
        trend: 'Trend',
        skills: 'Key Skills',
        trendingSkills: 'Trending Skills',
        marketInsights: 'Market Insights',
        footerText: 'Job Intelligence Dashboard © 2026. Updated',
        trendUp: 'Rising',
        trendDown: 'Declining',
        trendStable: 'Stable'
      },
      zh: {
        logo: '就业情报',
        heroTitle: '市场情报',
        heroSubtitle: '关于就业趋势、技能需求和市场动态的实时洞察',
        totalPostings: '活跃职位',
        growthRate: '年增长率',
        regionalOverview: '区域概览',
        latestRoles: '最新机会',
        role: '职位',
        company: '公司',
        location: '地点',
        salary: '薪资',
        trend: '趋势',
        skills: '关键技能',
        trendingSkills: '热门技能',
        marketInsights: '市场洞察',
        footerText: '就业情报仪表板 © 2026. 更新于',
        trendUp: '上升',
        trendDown: '下降',
        trendStable: '稳定'
      }
    };

    this.init();
  }

  async init() {
    try {
      await Promise.all([
        this.fetchSummary(),
        this.fetchRoles()
      ]);

      this.render();
      this.setupEventListeners();
    } catch (error) {
      console.error('Error initializing app:', error);
      this.showError();
    }
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

  render() {
    this.renderHero();
    this.renderMetrics();
    this.renderRegions();
    this.renderRolesTable();
    this.renderSkills();
    this.renderInsights();
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

    this.rolesData.forEach((role, index) => {
      const row = document.createElement('tr');
      row.style.animationDelay = `${index * 0.05}s`;

      const trendClass = `trend-${role.trend}`;
      const trendText = this.getTrendText(role.trend);
      const trendIcon = this.getTrendIcon(role.trend);

      row.innerHTML = `
        <td>
          <div class="role-name">${role.role}</div>
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
  }

  setupEventListeners() {
    const langToggle = document.getElementById('langToggle');
    langToggle.addEventListener('click', () => {
      const newLang = this.currentLang === 'en' ? 'zh' : 'en';
      this.updateLanguage(newLang);
    });
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
