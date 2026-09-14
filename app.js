/**
 * Tamskritam - Single Page Application Engine
 * Sanskrit Stotras Adapted into Metered Tamil Poetry by Sri R. Gururaj
 */

// Global State
const state = {
  works: [],
  searchIndex: [],
  currentWork: null,
  activeCategory: 'all',
  activeDeity: 'all',
  scriptFilter: 'both', // 'both' | 'tamil' | 'sanskrit'
  readingMode: 'cards', // 'cards' | 'chanting'
  fontSizeLevel: 1, // 0: Small, 1: Normal, 2: Large, 3: XL
  bookmarks: JSON.parse(localStorage.getItem('tamskritam-bookmarks') || '[]'),
  theme: localStorage.getItem('tamskritam-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
};

// Font size configurations
const FONT_SIZES = [
  { label: 'A-', verseSize: '1rem', saSize: '0.95rem' },
  { label: 'A', verseSize: '1.15rem', saSize: '1.1rem' },
  { label: 'A+', verseSize: '1.35rem', saSize: '1.25rem' },
  { label: 'A++', verseSize: '1.55rem', saSize: '1.45rem' }
];

/* ==========================================================================
   Theme Manager
   ========================================================================== */
const ThemeManager = {
  init() {
    this.apply(state.theme);
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => this.cycleTheme());
    }

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (!localStorage.getItem('tamskritam-theme')) {
        this.apply(e.matches ? 'dark' : 'light');
      }
    });
  },

  cycleTheme() {
    const themes = ['light', 'dark', 'sepia'];
    const currentIndex = themes.indexOf(state.theme);
    const nextTheme = themes[(currentIndex + 1) % themes.length];
    this.apply(nextTheme);
  },

  apply(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tamskritam-theme', theme);
    
    // Update Theme Toggle Button Icon & Accessible Label
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
      if (theme === 'dark') {
        themeBtn.innerHTML = '<i class="fa-solid fa-moon" aria-hidden="true"></i>';
        themeBtn.title = 'Current: Dark Mode (Click for Sepia)';
        themeBtn.setAttribute('aria-label', 'Current: Dark Mode. Click for Sepia');
      } else if (theme === 'sepia') {
        themeBtn.innerHTML = '<i class="fa-solid fa-scroll" aria-hidden="true"></i>';
        themeBtn.title = 'Current: Sepia Manuscript (Click for Light)';
        themeBtn.setAttribute('aria-label', 'Current: Sepia Manuscript. Click for Light');
      } else {
        themeBtn.innerHTML = '<i class="fa-solid fa-sun" aria-hidden="true"></i>';
        themeBtn.title = 'Current: Light Mode (Click for Dark)';
        themeBtn.setAttribute('aria-label', 'Current: Light Mode. Click for Dark');
      }
    }
  }
};

/* ==========================================================================
   Data & Cache Management
   ========================================================================== */
const DataManager = {
  workCache: {},

  async fetchWorksIndex() {
    if (state.works.length) return state.works;
    try {
      const res = await fetch('data/works_index.json');
      state.works = await res.json();
      return state.works;
    } catch (e) {
      console.error('Error fetching works index:', e);
      return [];
    }
  },

  async fetchWork(id) {
    if (this.workCache[id]) return this.workCache[id];
    try {
      const res = await fetch(`data/works/${id}.json`);
      const data = await res.json();
      this.workCache[id] = data;
      return data;
    } catch (e) {
      console.error(`Error fetching work ${id}:`, e);
      return null;
    }
  },

  async fetchSearchIndex() {
    if (state.searchIndex.length) return state.searchIndex;
    try {
      const res = await fetch('data/search_index.json');
      state.searchIndex = await res.json();
      return state.searchIndex;
    } catch (e) {
      console.error('Error fetching search index:', e);
      return [];
    }
  }
};

/* ==========================================================================
   Catalog & Filter View Helper Functions
   ========================================================================== */
const renderWorkIcon = (w) => {
  if (!w.icon) return '<i class="fa-solid fa-om" aria-hidden="true"></i>';
  if (w.icon.endsWith('.svg') || w.icon.startsWith('images/') || w.icon.includes('/')) {
    return `<img src="${w.icon}" alt="${w.title_ta || 'Work'} icon" class="work-icon-svg" loading="lazy">`;
  }
  if (w.icon.includes('fa-')) {
    return `<i class="${w.icon}" aria-hidden="true"></i>`;
  }
  return w.icon;
};

const getVerseBadgeText = (w) => {
  if (w.id === 'vishnu-sahasranamam-analysis') {
    return `${w.total_verses || 30} Chapters`;
  }
  const count = w.total_verses;
  return `${count} ${count === 1 ? 'Verse' : 'Verses'}`;
};

const renderAuthorInfo = (w, isReader = false) => {
  const authors = (w.authors && w.authors.length) ? w.authors : [
    { title: w.author_title || '', name: w.author_name || w.original_author || 'பாரம்பரியம்' }
  ];
  const work = w.source_work || '';

  const authorsHtml = authors.map((auth, idx) => {
    const titleText = auth.title ? `“${auth.title}”` : '';
    const hasNext = idx < authors.length - 1;
    return `
      <div class="author-line">
        <span class="author-pill${auth.title ? ' has-prefix' : ''}">
          ${auth.title ? `<span class="author-pill-prefix">${titleText}</span>` : ''}
          <span class="author-pill-name">${auth.name}</span>
        </span>
        ${hasNext ? `<span class="author-amp">&</span>` : ''}
      </div>
    `;
  }).join('');

  if (isReader) {
    return `
      <div class="reader-credit-item reader-credit-author">
        <span class="credit-label"><i class="fa-solid fa-feather-pointed" style="color:var(--accent-gold); margin-right:4px;" aria-hidden="true"></i> Original:</span>
        <div class="author-lines-container">
          ${authorsHtml}
          ${work ? `<div class="author-work-line"><span class="author-work-tag"><i class="fa-solid fa-book-open" aria-hidden="true"></i> ${work}</span></div>` : ''}
        </div>
      </div>
    `;
  }

  return `
    <div class="author-attribution">
      <i class="fa-solid fa-feather-pointed author-feather" aria-hidden="true"></i>
      <div class="author-lines-container">
        ${authorsHtml}
        ${work ? `<div class="author-work-line"><span class="author-work-tag"><i class="fa-solid fa-book-open" aria-hidden="true"></i> ${work}</span></div>` : ''}
      </div>
    </div>
  `;
};

/* ==========================================================================
   Catalog & Filter View
   ========================================================================== */
const CatalogView = {
  async render() {
    const catalogGrid = document.getElementById('works-grid');
    if (!catalogGrid) return;

    const works = await DataManager.fetchWorksIndex();
    
    // Filter works based on activeCategory and activeDeity
    const filtered = works.filter(w => {
      const matchCat = state.activeCategory === 'all' || 
                       w.category === state.activeCategory || 
                       (Array.isArray(w.categories) && w.categories.includes(state.activeCategory));
                       
      const matchDeity = state.activeDeity === 'all' || 
                         w.deity === state.activeDeity || 
                         (Array.isArray(w.deities) && w.deities.includes(state.activeDeity));
                         
      return matchCat && matchDeity;
    });

    if (!filtered.length) {
      catalogGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 4rem 1rem; color: var(--text-secondary);">
          <i class="fa-solid fa-magnifying-glass" style="font-size: 2.5rem; margin-bottom: 0.75rem; color: var(--text-tertiary);" aria-hidden="true"></i>
          <h3 style="font-family: var(--font-heading); font-size: 1.35rem; margin-bottom: 0.5rem;">No works found</h3>
          <p style="font-size: 0.95rem;">Please adjust your category or deity filters to view works.</p>
        </div>
      `;
      return;
    }

    catalogGrid.innerHTML = filtered.map(w => `
      <a href="#read/${w.id}" class="work-card">
        <div class="work-card-top">
          <div class="work-icon-box">${renderWorkIcon(w)}</div>
          <div class="work-badges-container">
            ${(w.illustrator || w.artist) ? `<span class="work-badge work-badge-illustrated"><i class="fa-solid fa-palette" aria-hidden="true"></i> Illustrated</span>` : ''}
            <span class="work-badge">${getVerseBadgeText(w)}</span>
            <span class="work-read-btn">Read <i class="fa-solid fa-arrow-right" style="margin-left:2px;" aria-hidden="true"></i></span>
          </div>
        </div>
        <div>
          <div class="work-title-sa">${w.title_sa || ''}</div>
          <h3 class="work-title-ta">${w.title_ta}</h3>
          <div class="work-title-en">${w.title_en || ''}</div>
          <p class="work-summary">${w.summary}</p>
        </div>
        <div class="work-card-footer">
          <div class="work-meta-info">
            ${renderAuthorInfo(w, false)}
          </div>
        </div>
      </a>
    `).join('');
  },

  setupFilters() {
    // Category Chips
    document.querySelectorAll('.cat-chip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.cat-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeCategory = btn.dataset.cat;
        this.render();
      });
    });

    // Deity Chips
    document.querySelectorAll('.deity-chip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.deity-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeDeity = btn.dataset.deity;
        this.render();
      });
    });
  }
};

/* ==========================================================================
   Reader View
   ========================================================================== */
const ReaderView = {
  async render(workId, targetVerseId = null, targetNama = null) {
    const work = await DataManager.fetchWork(workId);
    if (!work) {
      alert('Unable to load requested work.');
      window.location.hash = '#catalog';
      return;
    }

    state.currentWork = work;

    // Switch view visibility
    document.getElementById('catalog-view').style.display = 'none';
    document.getElementById('about-section').classList.remove('active');
    const readerContainer = document.getElementById('reader-view');
    readerContainer.classList.add('active');
    readerContainer.style.display = 'block';

    // Set toolbar title
    document.getElementById('reader-toolbar-title').textContent = work.title_ta;

    // Set header info
    document.getElementById('reader-sa-title').textContent = work.title_sa || '';
    document.getElementById('reader-ta-title').textContent = work.title_ta;
    document.getElementById('reader-en-title').textContent = work.title_en || '';
    
    // Set credits with structured compound author pill & multi-author support
    let creditsHtml = renderAuthorInfo(work, true);

    creditsHtml += `
      <div class="reader-credit-item">
        <span class="credit-label"><i class="fa-solid fa-pen-nib" style="color:var(--accent); margin-right:4px;" aria-hidden="true"></i> Tamil Verse Adaptation:</span>
        <strong class="credit-value">${work.translator || 'Sri R. Gururaj (ரா.குருராஜ்)'}</strong>
      </div>
    `;
    
    if (work.illustrator_name || work.illustrator || work.artist) {
      const illName = work.illustrator_name || work.illustrator || work.artist;
      
      creditsHtml += `
        <div class="reader-credit-item">
          <span class="credit-label"><i class="fa-solid fa-palette" style="color:var(--accent-gold); margin-right:4px;" aria-hidden="true"></i> Illustrator:</span>
          <strong class="credit-value">${illName}</strong>
        </div>
      `;
    }

    creditsHtml += `
      <div class="reader-credit-item">
        <span class="credit-label"><i class="fa-solid fa-layer-group" style="color:var(--accent-gold); margin-right:4px;" aria-hidden="true"></i> Total Verses:</span>
        <strong class="credit-value">${work.total_verses}</strong>
      </div>
    `;
    document.getElementById('reader-credits-container').innerHTML = creditsHtml;

    // Populate Section Dropdown
    this.setupSectionDropdown();

    // Render Verses
    this.renderVerses();
    this.updateReaderControls();
    this.setupAdjacentNav();

    // Scroll to top, specific verse, or specific nama
    if (targetNama) {
      setTimeout(() => {
        const namaNum = targetNama.replace('nama-', '');
        const verseEl = targetVerseId ? document.getElementById(`verse-${targetVerseId}`) : null;
        if (verseEl) {
          const details = verseEl.querySelector('.names-breakdown-details');
          if (details) details.open = true;
        }
        const namaEl = document.getElementById(`nama-${namaNum}`);
        if (namaEl) {
          namaEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          namaEl.classList.add('highlight-pulse');
          setTimeout(() => namaEl.classList.remove('highlight-pulse'), 2500);
        } else if (verseEl) {
          this.scrollToTarget(verseEl);
        }
      }, 180);
    } else if (targetVerseId) {
      setTimeout(() => {
        this.scrollToTarget(`verse-${targetVerseId}`);
      }, 150);
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  setupSectionDropdown() {
    const dropdownContainer = document.getElementById('reader-section-dropdown');
    const toggleBtn = document.getElementById('reader-section-toggle');
    const toggleText = document.getElementById('reader-section-toggle-text');
    const popover = document.getElementById('reader-section-popover');
    if (!dropdownContainer || !toggleBtn || !popover) return;

    const work = state.currentWork;
    if (!work || !work.sections || work.sections.length <= 1) {
      dropdownContainer.style.display = 'none';
      return;
    }

    dropdownContainer.style.display = 'inline-block';
    toggleText.textContent = `Jump to Section (${work.sections.length})...`;

    // Populate popover items with .index-num-icon circle badges
    let popoverHtml = '';
    work.sections.forEach((s, idx) => {
      let targetId = `sec-${idx}`;
      let isIndex = false;
      if (s.includes('பொருளடக்கம்') || s.includes('Index')) {
        targetId = 'andhadhi-index';
        isIndex = true;
      }

      let numBadge = '';
      let cleanTitle = s;

      const numMatch = s.match(/^(\d+)\)\s*(.*)$/);
      const partMatch = s.match(/^(?:பகுதி|பாகம்|Part|Chapter)\s*(\d+)[:\s-]*(.*)$/i);

      if (isIndex) {
        numBadge = '<i class="fa-solid fa-book-bookmark" aria-hidden="true" style="font-size:0.75rem;"></i>';
      } else if (numMatch) {
        numBadge = numMatch[1];
        cleanTitle = numMatch[2];
      } else if (partMatch) {
        numBadge = partMatch[1];
        cleanTitle = partMatch[2];
      } else {
        numBadge = '🪷';
      }

      popoverHtml += `
        <button class="section-dropdown-item" type="button" role="menuitem" data-target="${targetId}">
          <span class="index-num-icon">${numBadge}</span>
          <span class="section-item-title">${cleanTitle}</span>
        </button>
      `;
    });

    popover.innerHTML = popoverHtml;

    // Toggle menu open/close
    toggleBtn.onclick = (e) => {
      e.stopPropagation();
      const isOpen = popover.classList.toggle('open');
      toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    };

    // Item click handler
    popover.querySelectorAll('.section-dropdown-item').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const targetId = btn.dataset.target;
        popover.classList.remove('open');
        toggleBtn.setAttribute('aria-expanded', 'false');
        if (targetId) {
          this.scrollToTarget(targetId);
        }
      };
    });

    // Close on click outside
    if (!window._sectionDropdownGlobalCloseBound) {
      document.addEventListener('click', (e) => {
        const dd = document.getElementById('reader-section-dropdown');
        if (dd && !dd.contains(e.target)) {
          const pop = document.getElementById('reader-section-popover');
          const btn = document.getElementById('reader-section-toggle');
          if (pop) pop.classList.remove('open');
          if (btn) btn.setAttribute('aria-expanded', 'false');
        }
      });
      window._sectionDropdownGlobalCloseBound = true;
    }
  },

  getCircledNumber(n) {
    const num = parseInt(n, 10);
    if (isNaN(num)) return n;
    if (num >= 1 && num <= 20) {
      return String.fromCharCode(0x2460 + num - 1); // ① to ⑳
    } else if (num >= 21 && num <= 35) {
      return String.fromCharCode(0x3251 + num - 21); // ㉑ to ㉟
    } else if (num >= 36 && num <= 50) {
      return String.fromCharCode(0x32B1 + num - 36); // ㊱ to ㊿
    }
    return `(${num})`;
  },

  formatSectionOption(s) {
    if (!s) return '';
    if (s.includes('பொருளடக்கம்') || s.includes('Index')) {
      return '📖 பொருளடக்கம் (Index)';
    }
    const m1 = s.match(/^(\d+)\)\s*(.*)$/);
    if (m1) {
      return `${this.getCircledNumber(m1[1])} ${m1[2]}`;
    }
    const m2 = s.match(/^(?:பகுதி|பாகம்|Part|Chapter)\s*(\d+)[:\s-]*(.*)$/i);
    if (m2) {
      return `${this.getCircledNumber(m2[1])} ${m2[2]}`;
    }
    return s;
  },

  scrollToTarget(target) {
    if (!target) return;
    let el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el && typeof target === 'string') {
      if (target === 'sec-0' || target === 'andhadhi-index') {
        el = document.getElementById('andhadhi-index') || document.getElementById('sec-0');
      }
    }
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  renderVerses() {
    const container = document.getElementById('verses-container');
    if (!container || !state.currentWork) return;

    const verses = state.currentWork.verses;
    let lastSection = null;
    let html = '';

    // If work has an index (e.g. Andhadhi Ramayanam 45 chapters or Sahasranamam Analysis 16 chapters), render Index Card at top
    if (state.currentWork.index_chapters && state.currentWork.index_chapters.length > 0) {
      const chapterCount = state.currentWork.index_chapters.length;
      const countLabel = state.currentWork.id.includes('ramayanam') ? `${chapterCount} அத்தியாயங்கள்` : `${chapterCount} பகுதிகள்`;
      html += `
        <div class="andhadhi-index-card" id="andhadhi-index">
          <div class="andhadhi-index-header">
            <i class="fa-solid fa-book-bookmark" aria-hidden="true"></i> பொருளடக்கம் (Index - ${countLabel})
          </div>
          <div class="andhadhi-index-grid">
            ${state.currentWork.index_chapters.map(ch => {
              const numMatch = ch.title.match(/^(\d+)\)\s*(.*)$/);
              const chapterNum = numMatch ? numMatch[1] : (ch.chapter_num || '');
              const cleanTitle = numMatch ? numMatch[2] : ch.title;

              let secIdx = state.currentWork.sections.indexOf(ch.title);
              if (secIdx < 0) {
                secIdx = state.currentWork.sections.findIndex(s => s === cleanTitle || s.startsWith(`${chapterNum})`));
              }
              const targetSecId = secIdx >= 0 ? `sec-${secIdx}` : `sec-ch-${chapterNum}`;
              return `
                <a href="#${targetSecId}" class="andhadhi-index-link" onclick="ReaderView.scrollToTarget('${targetSecId}'); return false;">
                  <span class="index-num-icon">${chapterNum}</span>
                  <span class="index-title-text">${cleanTitle}</span>
                </a>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    verses.forEach((v, idx) => {
      // Check if section changed
      if (v.section && v.section !== lastSection) {
        const secIndex = state.currentWork.sections.indexOf(v.section);
        const secId = secIndex >= 0 ? `sec-${secIndex}` : `sec-${idx}`;
        
        const secNumMatch = v.section.match(/^(\d+)\)\s*(.*)$/);
        const secBadgeInnerHtml = secNumMatch
          ? `<span class="section-divider-num-icon">${secNumMatch[1]}</span> <span class="section-divider-title">${secNumMatch[2]}</span>`
          : `<span>🪷</span> <span class="section-divider-title">${v.section}</span>`;
        
        html += `
          <div class="section-divider" id="${secId}">
            <div class="section-divider-badge">
              ${secBadgeInnerHtml}
            </div>
          </div>
        `;
        lastSection = v.section;
      }

      // Format Tamil poetry lines
      let formattedTamilHtml = '';
      const isWorkNoIndent = state.currentWork.no_indent || v.is_intro;
      if (v.tamil) {
        const lines = v.tamil.split('\n');
        formattedTamilHtml = lines.map((l, lIdx) => {
          let isIndented = false;
          if (!isWorkNoIndent) {
            isIndented = l.startsWith('    ') || (lIdx % 2 === 1);
          } else if (l.startsWith('    ')) {
            isIndented = true;
          }
          const cleanLine = l.trim();
          return `<div class="tamil-poetry-line ${isIndented ? 'edhukai-indent' : ''}">${cleanLine}</div>`;
        }).join('');
      }

      // Handle unnumbered Chorus Refrain for Hanuman Chalisa
      if (v.is_refrain) {
        html += `
          <div class="chalisa-refrain-banner">
            <div class="chalisa-refrain-badge"><i class="fa-solid fa-hands-praying" aria-hidden="true"></i> ஜெயமனுமான் பல்லவி (Chorus)</div>
            <div class="chalisa-refrain-sa">${v.sanskrit}</div>
            <div class="chalisa-refrain-ta">${formattedTamilHtml}</div>
          </div>
        `;
        return;
      }

      const hasImages = v.images && v.images.length > 0;
      const isBookmarked = state.bookmarks.some(b => b.work_id === state.currentWork.id && b.verse_id === v.id);

      // Determine media layout class (configurable per-verse or work level)
      let mediaLayoutClass = '';
      if (hasImages) {
        if (v.media_layout) {
          mediaLayoutClass = v.media_layout;
        } else if (state.currentWork.media_layout) {
          mediaLayoutClass = state.currentWork.media_layout;
        } else if (v.images.length === 1) {
          mediaLayoutClass = 'media-single';
        } else if (v.images.length === 2) {
          mediaLayoutClass = 'media-pair';
        } else if (v.images.length <= 6) {
          mediaLayoutClass = 'media-gallery-small';
        } else {
          mediaLayoutClass = 'media-gallery-large';
        }
      }

      let badgeLabel = '';
      if (v.is_intro) {
        badgeLabel = 'அறிமுகம் (Introduction)';
      } else if (v.is_ending) {
        badgeLabel = 'நிறைவு / சமர்ப்பணம் (Conclusion)';
      } else if (v.verse_num) {
        if (/^\d+$/.test(v.verse_num)) {
          badgeLabel = `Verse ${v.verse_num}`;
        } else {
          badgeLabel = v.verse_num;
        }
      } else {
        badgeLabel = 'மங்களம் (Doha)';
      }

      // Render Centered Subheading (e.g. உத்தர நியாஸம்) if present
      if (v.subheading_sa || v.subheading_ta) {
        html += `
          <div class="verse-subheading-divider">
            <div class="verse-subheading-badge">
              <i class="fa-solid fa-om" aria-hidden="true" style="color:var(--accent-gold); margin-right:4px;"></i>
              ${v.subheading_sa ? `<span class="subheading-sa">${v.subheading_sa}</span>` : ''}
              ${v.subheading_sa && v.subheading_ta ? `<span class="subheading-sep">•</span>` : ''}
              ${v.subheading_ta ? `<span class="subheading-ta">${v.subheading_ta}</span>` : ''}
            </div>
          </div>
        `;
      }

      // Render Centered Speaker Banner (e.g. பீஷ்மர் பகர்ந்தார் / भीष्म उवाच) if present
      if (v.speaker_sa || v.speaker_ta) {
        html += `
          <div class="verse-speaker-divider">
            <div class="verse-speaker-badge">
              <i class="fa-solid fa-feather-pointed" aria-hidden="true" style="color:var(--accent-gold); margin-right:4px;"></i>
              ${v.speaker_sa ? `<span class="speaker-sa">${v.speaker_sa}</span>` : ''}
              ${v.speaker_sa && v.speaker_ta ? `<span class="speaker-sep">•</span>` : ''}
              ${v.speaker_ta ? `<span class="speaker-ta">${v.speaker_ta}</span>` : ''}
            </div>
          </div>
        `;
      }

      html += `
        <div class="verse-card ${v.is_ending ? 'verse-ending-card' : ''} ${v.is_intro ? 'verse-intro-card' : ''}" id="verse-${v.id}">
          <div class="verse-card-header">
            <div class="verse-number-badge">
              <span>${v.is_intro ? '📖' : (v.is_ending ? '🙏' : '🌸')}</span> ${badgeLabel}
            </div>
            <div class="verse-actions">
              <button class="verse-btn ${isBookmarked ? 'bookmarked' : ''}" onclick="BookmarksManager.toggle('${state.currentWork.id}', ${v.id})" aria-label="${isBookmarked ? 'Remove bookmark' : 'Bookmark verse'}" title="Bookmark Verse">
                ${isBookmarked ? '<i class="fa-solid fa-star" style="color:var(--accent-gold);" aria-hidden="true"></i>' : '<i class="fa-regular fa-star" aria-hidden="true"></i>'}
              </button>
              <button class="verse-btn" onclick="ReaderView.copyVerse(${v.id})" aria-label="Copy verse text" title="Copy Verse">
                <i class="fa-regular fa-copy" aria-hidden="true"></i>
              </button>
              <button class="verse-btn" onclick="ReaderView.shareVerse(${v.id})" aria-label="Share verse link" title="Share Link">
                <i class="fa-solid fa-share-nodes" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          
          <div class="verse-body ${hasImages ? 'has-media' : ''}">
            <div class="verse-text-content">
              ${v.sanskrit ? `
                <div class="verse-sanskrit">
                  ${v.sanskrit}
                  ${v.sanskrit_refrain ? `<div class="sanskrit-refrain-line">${v.sanskrit_refrain}</div>` : ''}
                </div>
              ` : ''}
              ${v.tamil ? `<div class="verse-tamil">${formattedTamilHtml}</div>` : ''}
              ${v.shloka_author ? `<div class="verse-shloka-author">${v.shloka_author}</div>` : ''}
              ${v.chorus ? `<div class="verse-chorus-line"><i class="fa-solid fa-om" style="margin-right:0.35rem;"></i> ${v.chorus}</div>` : ''}
              ${v.meaning ? `<div class="verse-meaning"><strong>Notes / Meaning:</strong> ${v.meaning}</div>` : ''}
              ${v.names_breakdown && v.names_breakdown.length > 0 ? `
                <details class="names-breakdown-details">
                  <summary class="names-breakdown-summary">
                    <i class="fa-solid fa-list-ol" aria-hidden="true"></i> <strong>திருநாமங்களின் விளக்கம் (${v.names_breakdown.length} திருநாமங்கள்)</strong>
                  </summary>
                  <div class="names-breakdown-grid">
                    ${v.names_breakdown.map(n => `
                      <div class="name-item-card" id="nama-${n.num}">
                        <div class="name-item-header">
                          <span class="name-number-badge">${n.num}</span>
                          <strong class="name-sa-text">${n.name_sa}</strong>
                        </div>
                        <div class="name-ta-meaning">${n.meaning_ta}</div>
                      </div>
                    `).join('')}
                  </div>
                </details>
              ` : ''}
              ${v.table_headers && v.table_rows && v.table_rows.length > 0 ? `
                <div class="analysis-table-container">
                  <table class="analysis-table">
                    <thead>
                      <tr>
                        ${v.table_headers.map(th => `<th>${th}</th>`).join('')}
                      </tr>
                    </thead>
                    <tbody>
                      ${v.table_rows.map(row => `
                        <tr>
                          ${row.map(cell => `<td>${cell}</td>`).join('')}
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              ` : ''}
            </div>
            
            ${hasImages ? `
              <div class="verse-media-container ${mediaLayoutClass}">
                ${v.images.map(img => `
                  <div class="verse-image-wrapper" onclick="Lightbox.open('${img}', '${state.currentWork.title_ta} - Verse ${v.verse_num || 'Introduction'}')" title="Click to view image in high-resolution">
                    <img src="${img}" alt="Illustration for ${state.currentWork.title_ta} verse ${v.verse_num || ''}" loading="lazy" onerror="this.parentElement.style.display='none'">
                    <span class="verse-zoom-hint"><i class="fa-solid fa-magnifying-glass-plus" aria-hidden="true"></i> Zoom</span>
                  </div>
                `).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  },

  updateReaderControls() {
    const root = document.getElementById('reader-view');
    
    // Script Display Classes
    root.classList.remove('hide-sanskrit', 'hide-tamil');
    if (state.scriptFilter === 'tamil') root.classList.add('hide-sanskrit');
    if (state.scriptFilter === 'sanskrit') root.classList.add('hide-tamil');

    // Reading Mode Class
    root.classList.toggle('chanting-mode', state.readingMode === 'chanting');

    // Font size styling
    const curSize = FONT_SIZES[state.fontSizeLevel];
    document.documentElement.style.setProperty('--verse-font-size', curSize.verseSize);
    document.documentElement.style.setProperty('--sanskrit-font-size', curSize.saSize);
  },

  setupAdjacentNav() {
    const works = state.works;
    const curIdx = works.findIndex(w => w.id === state.currentWork.id);
    const prevWork = curIdx > 0 ? works[curIdx - 1] : null;
    const nextWork = curIdx < works.length - 1 ? works[curIdx + 1] : null;

    const navFooter = document.getElementById('reader-nav-footer');
    if (navFooter) {
      navFooter.innerHTML = `
        ${prevWork ? `
          <a href="#read/${prevWork.id}" class="reader-nav-btn">
            <i class="fa-solid fa-arrow-left" aria-hidden="true"></i> Previous: ${prevWork.title_ta}
          </a>
        ` : '<div></div>'}
        <button class="reader-nav-btn" onclick="window.scrollTo({top:0, behavior:'smooth'})">
          <i class="fa-solid fa-arrow-up" aria-hidden="true"></i> Back to Top
        </button>
        ${nextWork ? `
          <a href="#read/${nextWork.id}" class="reader-nav-btn">
            Next: ${nextWork.title_ta} <i class="fa-solid fa-arrow-right" aria-hidden="true"></i>
          </a>
        ` : '<div></div>'}
      `;
    }
  },

  copyVerse(verseId) {
    const v = state.currentWork.verses.find(item => item.id === verseId);
    if (!v) return;
    const copyText = `✨ ${state.currentWork.title_ta} (Verse ${v.verse_num})\n${v.sanskrit ? '\n' + v.sanskrit : ''}\n\n${v.tamil}\n\nTamil: Sri R. Gururaj (ரா.குருராஜ்)\nLink: https://tamskritam.github.io/#read/${state.currentWork.id}`;
    navigator.clipboard.writeText(copyText).then(() => {
      alert('Verse copied to clipboard!');
    });
  },

  shareVerse(verseId) {
    const url = `${window.location.origin}${window.location.pathname}#read/${state.currentWork.id}/${verseId}`;
    if (navigator.share) {
      navigator.share({
        title: `${state.currentWork.title_ta} - Verse ${verseId}`,
        text: `${state.currentWork.title_ta} - Sanskrit to Tamil Adaptation`,
        url: url
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(() => {
        alert('Verse link copied to clipboard!');
      });
    }
  }
};

/* ==========================================================================
   Daily Shloka Feature
   ========================================================================== */
const DailyShlokaWidget = {
  async init() {
    const container = document.getElementById('daily-shloka-container');
    if (!container) return;

    const searchIndex = await DataManager.fetchSearchIndex();
    if (!searchIndex.length) return;

    // Pick verse based on day of year
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 0);
    const diff = now - start;
    const oneDay = 1000 * 60 * 60 * 24;
    const dayOfYear = Math.floor(diff / oneDay);

    // Pick high quality verse (prefer with both Sanskrit and Tamil)
    const candidates = searchIndex.filter(r => r.sanskrit && r.tamil && r.tamil.length > 30);
    const chosen = candidates[dayOfYear % candidates.length] || searchIndex[0];

    const dailyTamilHtml = chosen.tamil.split('\n').map((l, lIdx) => {
      const isIndented = l.startsWith('    ') || (lIdx % 2 === 1);
      const cleanLine = l.trim();
      return `<div class="tamil-poetry-line ${isIndented ? 'edhukai-indent' : ''}">${cleanLine}</div>`;
    }).join('');

    container.innerHTML = `
      <div class="daily-shloka-card">
        <div class="daily-shloka-header">
          <span class="daily-shloka-tag"><i class="fa-solid fa-sparkles" aria-hidden="true" style="margin-right:4px;"></i> Daily Verse of the Day</span>
          <a href="#read/${chosen.work_id}/${chosen.verse_id}" class="daily-shloka-work-link">
            ${chosen.work_title_ta} (Verse ${chosen.verse_num}) <i class="fa-solid fa-arrow-right" style="margin-left:4px;" aria-hidden="true"></i>
          </a>
        </div>
        ${chosen.sanskrit ? `<div class="daily-shloka-sa">${chosen.sanskrit}</div>` : ''}
        <div class="daily-shloka-ta">${dailyTamilHtml}</div>
        <div class="daily-shloka-actions">
          <button class="daily-shloka-copy-btn" onclick="navigator.clipboard.writeText('${chosen.sanskrit ? chosen.sanskrit.replace(/'/g, "\\'") + '\\n\\n' : ''}${chosen.tamil.replace(/'/g, "\\'")}').then(()=>alert('Verse copied to clipboard!'))" aria-label="Copy verse" title="Copy Verse">
            <i class="fa-regular fa-copy" aria-hidden="true"></i> Copy Verse
          </button>
          <a href="#read/${chosen.work_id}/${chosen.verse_id}" class="daily-shloka-read-btn" title="Read Full Work">
            <span>Read Full Work</span> <i class="fa-solid fa-arrow-right" aria-hidden="true"></i>
          </a>
        </div>
      </div>
    `;
  }
};

/* ==========================================================================
   Global Search Engine
   ========================================================================== */
const SearchModal = {
  init() {
    this.updateShortcutHint();
    const openBtns = document.querySelectorAll('.search-trigger-btn, .search-btn-nav');
    const closeBtn = document.getElementById('search-close-btn');
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-query-input');

    openBtns.forEach(btn => {
      btn.addEventListener('click', () => this.open());
    });

    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.close();
      });
    }

    if (input) {
      input.addEventListener('input', (e) => this.handleSearch(e.target.value));
    }

    // Keyboard shortcut (⌘K / Ctrl+K)
    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.open();
      }
      if (e.key === 'Escape' && modal.classList.contains('open')) {
        this.close();
      }
    });
  },

  updateShortcutHint() {
    const isMac = /(Mac|iPhone|iPod|iPad)/i.test(
      navigator.userAgentData?.platform || navigator.platform || navigator.userAgent || ''
    );
    const kbdText = isMac ? '⌘K' : 'Ctrl K';
    const titleText = isMac ? '⌘K' : 'Ctrl+K';

    document.querySelectorAll('.search-kbd').forEach(el => {
      el.textContent = kbdText;
    });

    document.querySelectorAll('.search-trigger-btn, .search-btn-nav').forEach(btn => {
      btn.setAttribute('aria-label', `Search verses and works (${titleText})`);
      btn.setAttribute('title', `Search verses and works (${titleText})`);
    });
  },

  async open() {
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-query-input');
    modal.classList.add('open');
    input.focus();
    await DataManager.fetchSearchIndex();
  },

  close() {
    const modal = document.getElementById('search-modal');
    modal.classList.remove('open');
  },

  handleSearch(query) {
    const resultsContainer = document.getElementById('search-results-list');
    const cleanQuery = query.trim().toLowerCase();

    if (!cleanQuery || cleanQuery.length < 2) {
      resultsContainer.innerHTML = `
        <div style="text-align: center; color: var(--text-tertiary); padding: 2rem 0;">
          Type a word, deity name, or verse line to search across all texts...
        </div>
      `;
      return;
    }

    const index = state.searchIndex;
    const matches = [];

    for (const item of index) {
      const saMatch = item.sanskrit && item.sanskrit.toLowerCase().includes(cleanQuery);
      const taMatch = item.tamil && item.tamil.toLowerCase().includes(cleanQuery);
      const namesMatch = item.names_text && item.names_text.toLowerCase().includes(cleanQuery);
      const meaningMatch = item.meaning && item.meaning.toLowerCase().includes(cleanQuery);
      const workMatch = item.work_title_ta && item.work_title_ta.toLowerCase().includes(cleanQuery);

      if (saMatch || taMatch || namesMatch || meaningMatch || workMatch) {
        matches.push({
          ...item,
          matchedNames: namesMatch
        });
        if (matches.length >= 40) break; // Cap search display at 40
      }
    }

    if (!matches.length) {
      resultsContainer.innerHTML = `
        <div style="text-align: center; color: var(--text-secondary); padding: 2.5rem 0;">
          No matching verses found for "${query}".
        </div>
      `;
      return;
    }

    // Highlight matches
    const highlight = (txt) => {
      if (!txt) return '';
      const regex = new RegExp(`(${cleanQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      return txt.replace(regex, '<mark>$1</mark>');
    };

    resultsContainer.innerHTML = matches.map(m => `
      <div class="search-result-item" onclick="SearchModal.selectResult('${m.work_id}', ${m.verse_id})">
        <div class="search-result-work"><i class="fa-solid fa-book-open" style="margin-right:4px;" aria-hidden="true"></i> ${m.work_title_ta} • Verse ${m.verse_num} ${m.section ? `(${m.section})` : ''}</div>
        ${m.sanskrit ? `<div class="search-result-text" style="font-family:var(--font-sanskrit); color:var(--accent-gold);">${highlight(m.sanskrit.substring(0, 140))}...</div>` : ''}
        ${m.tamil ? `<div class="search-result-text" style="font-family:var(--font-tamil);">${highlight(m.tamil.substring(0, 160))}...</div>` : ''}
        ${m.matchedNames && m.names_text ? `<div class="search-result-text" style="font-size:0.85rem; color:var(--accent-gold);"><i class="fa-solid fa-list-ol"></i> ${highlight(m.names_text.substring(0, 200))}...</div>` : ''}
      </div>
    `).join('');
  },

  selectResult(workId, verseId) {
    this.close();
    window.location.hash = `#read/${workId}/${verseId}`;
  }
};

/* ==========================================================================
   Bookmarks Manager
   ========================================================================== */
const BookmarksManager = {
  init() {
    const btn = document.getElementById('bookmarks-btn');
    const modal = document.getElementById('bookmarks-modal');
    const closeBtn = document.getElementById('bookmarks-close-btn');

    if (btn) btn.addEventListener('click', () => this.open());
    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.close();
      });
    }

    this.updateCountBadge();
  },

  open() {
    const modal = document.getElementById('bookmarks-modal');
    this.renderList();
    modal.classList.add('open');
  },

  close() {
    const modal = document.getElementById('bookmarks-modal');
    modal.classList.remove('open');
  },

  async toggle(workId, verseId) {
    const existsIdx = state.bookmarks.findIndex(b => b.work_id === workId && b.verse_id === verseId);
    
    if (existsIdx >= 0) {
      state.bookmarks.splice(existsIdx, 1);
    } else {
      const work = await DataManager.fetchWork(workId);
      const v = work ? work.verses.find(item => item.id === verseId) : null;
      if (v) {
        state.bookmarks.push({
          work_id: workId,
          work_title_ta: work.title_ta,
          verse_id: verseId,
          verse_num: v.verse_num,
          sanskrit: (v.sanskrit || '').substring(0, 100),
          tamil: (v.tamil || '').substring(0, 120),
          added_at: Date.now()
        });
      }
    }

    localStorage.setItem('tamskritam-bookmarks', JSON.stringify(state.bookmarks));
    this.updateCountBadge();
    
    // Update active verse card button UI if in reader
    if (state.currentWork && state.currentWork.id === workId) {
      const btn = document.querySelector(`#verse-${verseId} .verse-btn`);
      if (btn) {
        const isBookmarked = state.bookmarks.some(b => b.work_id === workId && b.verse_id === verseId);
        btn.classList.toggle('bookmarked', isBookmarked);
        btn.innerHTML = isBookmarked 
          ? '<i class="fa-solid fa-star" style="color:var(--accent-gold);" aria-hidden="true"></i>' 
          : '<i class="fa-regular fa-star" aria-hidden="true"></i>';
        btn.setAttribute('aria-label', isBookmarked ? 'Remove bookmark' : 'Bookmark verse');
      }
    }
  },

  updateCountBadge() {
    const badge = document.getElementById('bookmarks-count-badge');
    if (badge) {
      badge.textContent = state.bookmarks.length;
      badge.style.display = state.bookmarks.length > 0 ? 'inline-block' : 'none';
    }
  },

  renderList() {
    const list = document.getElementById('bookmarks-list');
    if (!list) return;

    if (!state.bookmarks.length) {
      list.innerHTML = `
        <div style="text-align: center; color: var(--text-tertiary); padding: 3rem 1rem;">
          <i class="fa-regular fa-bookmark" style="font-size: 2.5rem; margin-bottom: 0.75rem; color: var(--accent-gold);" aria-hidden="true"></i>
          <h4 style="font-family: var(--font-heading); font-size: 1.2rem;">No Saved Verses Yet</h4>
          <p style="font-size: 0.9rem; margin-top: 0.25rem;">Click the star icon (<i class="fa-regular fa-star" aria-hidden="true"></i>) on any verse card to save it for quick reference.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = state.bookmarks.map(b => `
      <div class="search-result-item" style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div onclick="BookmarksManager.selectBookmark('${b.work_id}', ${b.verse_id})" style="flex:1;">
          <div class="search-result-work"><i class="fa-solid fa-book-open" style="margin-right:4px;" aria-hidden="true"></i> ${b.work_title_ta} • Verse ${b.verse_num}</div>
          ${b.sanskrit ? `<div style="font-family:var(--font-sanskrit); color:var(--accent-gold); font-size:0.9rem;">${b.sanskrit}...</div>` : ''}
          <div style="font-family:var(--font-tamil); font-size:0.95rem; color:var(--text-primary);">${b.tamil}...</div>
        </div>
        <button onclick="BookmarksManager.toggle('${b.work_id}', ${b.verse_id}); BookmarksManager.renderList();" style="color:var(--text-tertiary); font-size:1.1rem; padding:0.25rem 0.5rem;" aria-label="Remove bookmark" title="Remove">
          <i class="fa-solid fa-trash-can" aria-hidden="true"></i>
        </button>
      </div>
    `).join('');
  },

  selectBookmark(workId, verseId) {
    this.close();
    window.location.hash = `#read/${workId}/${verseId}`;
  }
};

/* ==========================================================================
   Image Lightbox Modal
   ========================================================================== */
const Lightbox = {
  init() {
    const modal = document.getElementById('lightbox-modal');
    const closeBtn = document.getElementById('lightbox-close-btn');

    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.close();
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('open')) {
        this.close();
      }
    });
  },

  open(imgSrc, caption = '') {
    const modal = document.getElementById('lightbox-modal');
    const imgEl = document.getElementById('lightbox-img');
    const captionEl = document.getElementById('lightbox-caption');

    imgEl.src = imgSrc;
    if (captionEl) captionEl.textContent = caption;
    modal.classList.add('open');
  },

  close() {
    const modal = document.getElementById('lightbox-modal');
    modal.classList.remove('open');
  }
};

/* ==========================================================================
   SPA Router & Navigation
   ========================================================================== */
const Router = {
  init() {
    window.addEventListener('hashchange', () => this.route());
    this.route();
  },

  async route() {
    const hash = window.location.hash || '#catalog';
    const catalogView = document.getElementById('catalog-view');
    const readerView = document.getElementById('reader-view');
    const aboutSection = document.getElementById('about-section');

    // Update Nav Link Active States
    document.querySelectorAll('.nav-link').forEach(link => {
      const href = link.getAttribute('href');
      link.classList.toggle('active', href === hash);
    });

    if (hash.startsWith('#read/')) {
      const parts = hash.replace('#read/', '').split('/');
      const workId = parts[0];
      const verseId = parts[1] ? parseInt(parts[1], 10) : null;
      const targetNama = parts[2] ? parts[2] : null;
      await ReaderView.render(workId, verseId, targetNama);
    } else if (hash === '#about') {
      catalogView.style.display = 'none';
      readerView.classList.remove('active');
      readerView.style.display = 'none';
      aboutSection.classList.add('active');
      aboutSection.style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      // Catalog / Home
      readerView.classList.remove('active');
      readerView.style.display = 'none';
      aboutSection.classList.remove('active');
      aboutSection.style.display = 'none';
      catalogView.style.display = 'block';
      await CatalogView.render();

      if (hash === '#catalog' || hash === '#filter-section') {
        const filterSec = document.getElementById('filter-section') || document.querySelector('.filter-section');
        if (filterSec) {
          filterSec.scrollIntoView({ behavior: 'smooth' });
        } else {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  }
};

/* ==========================================================================
   App Initialization
   ========================================================================== */
document.addEventListener('DOMContentLoaded', async () => {
  ThemeManager.init();
  CatalogView.setupFilters();
  SearchModal.init();
  BookmarksManager.init();
  Lightbox.init();

  // Setup Segmented Controls in Reader Toolbar
  document.querySelectorAll('[data-script]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-script]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.scriptFilter = btn.dataset.script;
      ReaderView.updateReaderControls();
    });
  });

  document.querySelectorAll('[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-mode]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.readingMode = btn.dataset.mode;
      ReaderView.updateReaderControls();
    });
  });

  // Font Size Buttons
  const fontIncBtn = document.getElementById('font-increase-btn');
  const fontDecBtn = document.getElementById('font-decrease-btn');
  if (fontIncBtn) {
    fontIncBtn.addEventListener('click', () => {
      if (state.fontSizeLevel < FONT_SIZES.length - 1) {
        state.fontSizeLevel++;
        ReaderView.updateReaderControls();
      }
    });
  }
  if (fontDecBtn) {
    fontDecBtn.addEventListener('click', () => {
      if (state.fontSizeLevel > 0) {
        state.fontSizeLevel--;
        ReaderView.updateReaderControls();
      }
    });
  }

  // Print Action Button
  const printBtn = document.getElementById('reader-print-btn');
  if (printBtn) {
    printBtn.addEventListener('click', () => window.print());
  }

  // Smooth scroll to Category filter section on clicking #catalog links
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href="#catalog"]');
    if (link && (window.location.hash === '#catalog' || !window.location.hash)) {
      const filterSec = document.getElementById('filter-section') || document.querySelector('.filter-section');
      if (filterSec) {
        e.preventDefault();
        filterSec.scrollIntoView({ behavior: 'smooth' });
      }
    }
  });

  // Pre-fetch catalog & initial route
  await DataManager.fetchWorksIndex();
  await DailyShlokaWidget.init();
  Router.init();
});
