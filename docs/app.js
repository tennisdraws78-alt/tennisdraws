/* Tennis Entry List Tracker — Interactive SPA */
(function () {
"use strict";

var D = window.TENNIS_DATA || { players: [], weeks: [], tournaments: [], stats: {} };

// Filter out past weeks — only keep from the current week onward
// (plus the most recent past week if it has entries from this week's tournaments)
(function filterPastWeeks() {
    var now = new Date();
    var MONTH_MAP = {
        "Jan": 0, "Feb": 1, "Mar": 2, "Apr": 3, "May": 4, "Jun": 5,
        "Jul": 6, "Aug": 7, "Sep": 8, "Oct": 9, "Nov": 10, "Dec": 11
    };

    function parseWeek(w) {
        var parts = w.split(" ");
        if (parts.length < 2) return null;
        var mon = MONTH_MAP[parts[0]];
        if (mon === undefined) return null;
        var day = parseInt(parts[1], 10);
        if (isNaN(day)) return null;
        var year = now.getFullYear();
        var dt = new Date(year, mon, day);
        // Handle year boundary: if the date is >6 months in the past,
        // it likely belongs to next year (e.g. "Jan 5" parsed in Dec)
        if (now - dt > 180 * 24 * 60 * 60 * 1000) {
            dt = new Date(year + 1, mon, day);
        }
        return dt;
    }

    // Find the cutoff: keep weeks whose start date is within 10 days before today
    // (i.e. the current week's tournament may have started a few days ago)
    var cutoff = new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000);

    var filtered = [];
    for (var i = 0; i < D.weeks.length; i++) {
        var dt = parseWeek(D.weeks[i]);
        if (!dt || dt >= cutoff) {
            filtered.push(D.weeks[i]);
        }
    }
    D.weeks = filtered;
})();

// === TOURNAMENT METADATA LOOKUP ===
var tournamentMeta = {};
(function buildTournamentMeta() {
    var ts = D.tournaments || [];
    for (var i = 0; i < ts.length; i++) {
        var t = ts[i];
        var key = (t.name || "").toLowerCase() + "|" + (t.gender || "").toLowerCase();
        if (!tournamentMeta[key]) tournamentMeta[key] = t;
    }
})();

function lookupSurface(tournamentName, gender) {
    var key = (tournamentName || "").toLowerCase() + "|" + (gender || "").toLowerCase();
    var meta = tournamentMeta[key];
    return meta ? meta.surface : "";
}

// === COUNTRY NAME LOOKUP ===
var COUNTRY_NAMES = {
    "AFG":"Afghanistan","ALB":"Albania","ALG":"Algeria","AND":"Andorra","ANG":"Angola",
    "ANT":"Antigua and Barbuda","ARG":"Argentina","ARM":"Armenia","ARU":"Aruba","AUS":"Australia",
    "AUT":"Austria","AZE":"Azerbaijan","BAH":"Bahamas","BDI":"Burundi","BEL":"Belgium",
    "BEN":"Benin","BER":"Bermuda","BIH":"Bosnia and Herzegovina","BLR":"Belarus","BOL":"Bolivia",
    "BOT":"Botswana","BRA":"Brazil","BRN":"Bahrain","BRU":"Brunei","BGR":"Bulgaria",
    "BUL":"Bulgaria","BUR":"Burkina Faso","CAM":"Cambodia","CAN":"Canada","CHE":"Switzerland",
    "CHI":"Chile","CHL":"Chile","CHN":"China","CIV":"Ivory Coast","CMR":"Cameroon",
    "COD":"DR Congo","COL":"Colombia","CRC":"Costa Rica","CRO":"Croatia","CUB":"Cuba",
    "CYP":"Cyprus","CZE":"Czechia","DEU":"Germany","DEN":"Denmark","DNK":"Denmark",
    "DOM":"Dominican Republic","ECU":"Ecuador","EGY":"Egypt","ESA":"El Salvador","ESP":"Spain",
    "EST":"Estonia","ETH":"Ethiopia","FIN":"Finland","FRA":"France","GBR":"Great Britain",
    "GEO":"Georgia","GER":"Germany","GHA":"Ghana","GRC":"Greece","GRE":"Greece",
    "GUA":"Guatemala","HAI":"Haiti","HKG":"Hong Kong","HON":"Honduras","HRV":"Croatia",
    "HUN":"Hungary","IDN":"Indonesia","INA":"Indonesia","IND":"India","IRI":"Iran",
    "IRL":"Ireland","IRQ":"Iraq","ISR":"Israel","ITA":"Italy","JAM":"Jamaica",
    "JOR":"Jordan","JPN":"Japan","KAZ":"Kazakhstan","KEN":"Kenya","KGZ":"Kyrgyzstan",
    "KOR":"South Korea","KSA":"Saudi Arabia","KUW":"Kuwait","LAT":"Latvia","LBN":"Lebanon",
    "LIB":"Libya","LIE":"Liechtenstein","LTU":"Lithuania","LUX":"Luxembourg","LVA":"Latvia",
    "MAR":"Morocco","MAS":"Malaysia","MDA":"Moldova","MEX":"Mexico","MKD":"North Macedonia",
    "MLT":"Malta","MNE":"Montenegro","MON":"Monaco","MCO":"Monaco","MRI":"Mauritius",
    "NED":"Netherlands","NLD":"Netherlands","NEP":"Nepal","NGR":"Nigeria","NOR":"Norway",
    "NZL":"New Zealand","OMA":"Oman","PAK":"Pakistan","PAN":"Panama","PAR":"Paraguay",
    "PER":"Peru","PHL":"Philippines","POL":"Poland","POR":"Portugal","PRT":"Portugal",
    "PRY":"Paraguay","PUR":"Puerto Rico","QAT":"Qatar","ROU":"Romania","RSA":"South Africa",
    "RUS":"Russia","RWA":"Rwanda","SEN":"Senegal","SRB":"Serbia","SGP":"Singapore",
    "SLO":"Slovenia","SVK":"Slovakia","SVN":"Slovenia","SRI":"Sri Lanka","SUD":"Sudan",
    "SUI":"Switzerland","SWE":"Sweden","SYR":"Syria","THA":"Thailand","TJK":"Tajikistan",
    "TKM":"Turkmenistan","TPE":"Chinese Taipei","TUN":"Tunisia","TUR":"Turkey","TWN":"Chinese Taipei",
    "UAE":"UAE","UGA":"Uganda","UKR":"Ukraine","URY":"Uruguay","USA":"United States",
    "UZB":"Uzbekistan","VEN":"Venezuela","VIE":"Vietnam","ZAF":"South Africa","ZIM":"Zimbabwe"
};

function countryName(code) {
    if (!code) return "";
    return COUNTRY_NAMES[code.toUpperCase()] || code;
}

// === STATE ===
var state = {
    gender: "all",
    search: "",
    entriesOnly: false,
    rankMin: 1,
    rankMax: 1500,
    currentView: "",           // "dashboard", "tournaments", "player", "tournament"
    tournamentTierFilter: "all",
    tournamentSection: "all",
};

// === UTILITIES ===
function esc(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function getBadgeClass(tier) {
    if (!tier) return "badge-other";
    var t = tier.toLowerCase();
    if (t.indexOf("grand slam") !== -1) return "badge-grand-slam";
    if (t.indexOf("1000") !== -1) return "badge-1000";
    if (t.indexOf("500") !== -1) return "badge-500";
    if (t.indexOf("250") !== -1) return "badge-250";
    if (t.indexOf("challenger") !== -1) return "badge-challenger";
    if (t.indexOf("125") !== -1) return "badge-125";
    if (t.indexOf("itf") !== -1) return "badge-itf";
    return "badge-other";
}

function getTierColorClass(tier) {
    if (!tier) return "tier-other";
    var t = tier.toLowerCase();
    if (t.indexOf("grand slam") !== -1) return "tier-grand-slam";
    if (t.indexOf("1000") !== -1) return "tier-1000";
    if (t.indexOf("500") !== -1) return "tier-500";
    if (t.indexOf("250") !== -1) return "tier-250";
    if (t.indexOf("challenger") !== -1) return "tier-challenger";
    if (t.indexOf("125") !== -1) return "tier-125";
    if (t.indexOf("itf") !== -1) return "tier-itf";
    return "tier-other";
}

function shortSection(section) {
    if (!section) return "";
    var s = section.toLowerCase();
    if (s.indexOf("main") !== -1) return "MD";
    if (s === "qualifying") return "Q";
    if (s.indexOf("qualifying") !== -1 && s.indexOf("alt") !== -1) return "QA";
    if (s.indexOf("alternate") !== -1) return "ALT";
    if (s.indexOf("wild") !== -1) return "WC";
    return section.substring(0, 3).toUpperCase();
}

function entriesByWeek(entries) {
    var map = {};
    for (var i = 0; i < entries.length; i++) {
        var w = entries[i].week || "__none__";
        if (!map[w]) map[w] = [];
        map[w].push(entries[i]);
    }
    return map;
}

function encName(name) {
    return encodeURIComponent(name);
}

function decName(name) {
    return decodeURIComponent(name);
}

// Build a player lookup index for fast access
var playerIndex = {};
for (var i = 0; i < D.players.length; i++) {
    var p = D.players[i];
    playerIndex[p.name.toLowerCase()] = p;
}

// Build tournament lookup (gender-aware: "dubai|women" vs "dubai|men")
function buildTournamentEntries() {
    var map = {};
    for (var pi = 0; pi < D.players.length; pi++) {
        var player = D.players[pi];
        var genderKey = (player.gender || "").toLowerCase();
        for (var ei = 0; ei < player.entries.length; ei++) {
            var e = player.entries[ei];
            var key = e.tournament.toLowerCase() + "|" + genderKey;
            if (!map[key]) {
                map[key] = {
                    name: e.tournament,
                    tier: e.tier,
                    week: e.week,
                    gender: player.gender,
                    entries: [],
                    sections: {},
                };
            }
            map[key].entries.push({
                rank: player.rank,
                name: player.name,
                gender: player.gender,
                country: player.country,
                section: e.section,
                source: e.source,
                withdrawn: e.withdrawn,
                reason: e.reason || "",
                withdrawal_type: e.withdrawal_type || "",
                entry_method: e.entry_method || "",
            });
            map[key].sections[e.section] = true;
        }
    }
    // Sort entries by rank
    var keys = Object.keys(map);
    for (var ki = 0; ki < keys.length; ki++) {
        map[keys[ki]].entries.sort(function (a, b) { return a.rank - b.rank; });
    }

    // Merge full entry lists (Challenger + WTA 125) from D.fullEntries
    if (D.fullEntries) {
        var feKeys = Object.keys(D.fullEntries);
        for (var fi = 0; fi < feKeys.length; fi++) {
            var feKey = feKeys[fi];
            var fe = D.fullEntries[feKey];
            if (!map[feKey]) {
                map[feKey] = {
                    name: fe.name,
                    tier: fe.tier,
                    week: fe.week,
                    gender: fe.gender || "",
                    entries: [],
                    sections: {},
                    hasFullList: true,
                };
            } else {
                map[feKey].hasFullList = true;
            }
            // Build full player list from compact format
            var fullPlayers = [];
            for (var fpi = 0; fpi < fe.players.length; fpi++) {
                var fp = fe.players[fpi];
                fullPlayers.push({
                    rank: fp.r || 0,
                    name: fp.n,
                    gender: fe.gender || "Women",
                    country: fp.c,
                    section: fp.s || "Main Draw",
                    source: fe.source || "",
                    withdrawn: fp.w || false,
                    entry_method: fp.m || "",
                });
            }
            // Replace entries with full list
            map[feKey].entries = fullPlayers;
            // Rebuild sections
            map[feKey].sections = {};
            for (var si = 0; si < fullPlayers.length; si++) {
                map[feKey].sections[fullPlayers[si].section] = true;
            }
        }
    }

    return map;
}
var tournamentEntries = buildTournamentEntries();

// === STATS ===
function renderStats() {
    var s = D.stats;
    document.getElementById("statPlayers").textContent = (s.totalPlayers || 0).toLocaleString();
    document.getElementById("statMatched").textContent = (s.playersWithEntries || 0).toLocaleString();
    document.getElementById("statEntries").textContent = (s.totalEntries || 0).toLocaleString();
    document.getElementById("statTournaments").textContent = (s.uniqueTournaments || 0).toLocaleString();
    document.getElementById("lastUpdated").textContent = "Updated: " + (s.generatedAt || "");
}

// === FILTERS ===
function applyFilters(players) {
    var searchLower = state.search.toLowerCase();
    var filtered = [];
    for (var i = 0; i < players.length; i++) {
        var p = players[i];
        if (state.gender !== "all" && p.gender !== state.gender) continue;
        if (state.entriesOnly && p.entries.length === 0) continue;
        if (p.rank < state.rankMin || p.rank > state.rankMax) continue;
        if (searchLower) {
            var found = false;
            if (p.name.toLowerCase().indexOf(searchLower) !== -1) found = true;
            if (!found && p.country && p.country.toLowerCase().indexOf(searchLower) !== -1) found = true;
            if (!found) {
                for (var j = 0; j < p.entries.length; j++) {
                    if (p.entries[j].tournament.toLowerCase().indexOf(searchLower) !== -1) { found = true; break; }
                }
            }
            if (!found) continue;
        }
        filtered.push(p);
    }
    return filtered;
}

// === RESET FILTERS ===
function resetFilters() {
    state.search = "";
    state.gender = "all";
    state.entriesOnly = false;
    state.rankMin = 1;
    state.rankMax = 1500;
    document.getElementById("searchInput").value = "";
    document.getElementById("entriesOnly").checked = false;
    document.getElementById("rankMin").value = "";
    document.getElementById("rankMax").value = "";
    var genderBtns = document.querySelectorAll(".gender-tabs button");
    for (var i = 0; i < genderBtns.length; i++) {
        genderBtns[i].classList.remove("active");
        if (genderBtns[i].getAttribute("data-gender") === "all") genderBtns[i].classList.add("active");
    }
    if (state.currentView === "dashboard") renderDashboard();
}

// === ROUTER ===
function route() {
    var hash = window.location.hash || "#/";
    var app = document.getElementById("app");
    var controls = document.getElementById("controls");
    var resultsCount = document.getElementById("resultsCount");

    // Clean up scroll handler from dashboard when navigating away
    if (app._scrollHandler) {
        window.removeEventListener("scroll", app._scrollHandler);
        app._scrollHandler = null;
    }

    // Update nav links
    var navLinks = document.querySelectorAll(".nav-link");
    for (var i = 0; i < navLinks.length; i++) {
        navLinks[i].classList.remove("active");
    }

    if (hash === "#/" || hash === "#" || hash === "") {
        // Dashboard
        state.currentView = "dashboard";
        controls.classList.remove("hidden");
        resultsCount.style.display = "";
        var dashNav = document.querySelector('[data-nav="dashboard"]');
        if (dashNav) dashNav.classList.add("active");
        renderDashboard();
    } else if (hash.indexOf("#/player/") === 0) {
        var playerName = decName(hash.substring(9));
        state.currentView = "player";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        renderPlayerProfile(playerName);
    } else if (hash === "#/tournaments") {
        state.currentView = "tournaments";
        state.tournamentTierFilter = "all";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        var tournNav = document.querySelector('[data-nav="tournaments"]');
        if (tournNav) tournNav.classList.add("active");
        renderTournamentBrowser();
    } else if (hash === "#/entry-lists") {
        state.currentView = "entry-lists";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        var elNav = document.querySelector('[data-nav="entry-lists"]');
        if (elNav) elNav.classList.add("active");
        state.tournamentTierFilter = "challenger-125";
        renderTournamentBrowser();
    } else if (hash === "#/withdrawals") {
        state.currentView = "withdrawals";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        var wdNav = document.querySelector('[data-nav="withdrawals"]');
        if (wdNav) wdNav.classList.add("active");
        renderWithdrawals();
    } else if (hash === "#/itf") {
        state.currentView = "itf";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        var itfNav = document.querySelector('[data-nav="itf"]');
        if (itfNav) itfNav.classList.add("active");
        renderITFBrowser();
    } else if (hash.indexOf("#/itf-tournament/") === 0) {
        var itfKey = decName(hash.substring(17));
        state.currentView = "itf-tournament";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        var itfNav = document.querySelector('[data-nav="itf"]');
        if (itfNav) itfNav.classList.add("active");
        renderITFTournamentDetail(itfKey);
    } else if (hash.indexOf("#/tournament/") === 0) {
        var tournParts = hash.substring(13).split("|");
        var tournName = decName(tournParts[0]);
        var tournGender = tournParts[1] ? decName(tournParts[1]) : "";
        state.currentView = "tournament";
        controls.classList.add("hidden");
        resultsCount.style.display = "none";
        renderTournamentDetail(tournName, tournGender);
    } else {
        // Fallback to dashboard
        window.location.hash = "#/";
    }

    // Re-trigger fade animation
    app.style.animation = "none";
    app.offsetHeight; // force reflow
    app.style.animation = "";
}

// === BADGE COMPONENT ===
function badgeHTML(entry, linkToTournament) {
    var cls = "badge-neutral";
    var wdCls = entry.withdrawn ? " withdrawn" : "";
    var sec = shortSection(entry.section);
    var secHTML = (sec && sec !== "MD") ? '<span class="section-indicator">' + sec + '</span>' : "";

    // Show entry_method indicator (WC, PR, LL, SE) — replaces section when MD
    var em = entry.entry_method || "";
    if (em) {
        var emSpan = '<span class="entry-method-indicator">' + esc(em) + '</span>';
        if (sec === "MD" || !sec) {
            secHTML = emSpan;  // WC replaces hidden MD indicator
        } else {
            secHTML += emSpan; // Q + WC both shown for qualifying wildcards
        }
    }

    var isRet = entry.withdrawal_type === "RET";
    var wdHTML = "";
    if (entry.withdrawn) {
        wdHTML = isRet ? ' <span class="ret-tag">RET</span>' : ' <span class="wd-tag">WD</span>';
    }
    var tierColorCls = getTierColorClass(entry.tier);
    var tierLabel = entry.tier ? '<span class="badge-tier-label ' + tierColorCls + '">' + esc(entry.tier) + '</span>' : "";
    var surface = lookupSurface(entry.tournament, entry.gender);
    var surfaceHTML = "";
    if (surface) {
        var sfcCls = "sfc-" + surface.toLowerCase();
        surfaceHTML = '<span class="badge-surface ' + sfcCls + '">' + esc(surface).toUpperCase() + '</span>';
    }
    var title = esc(entry.tournament) + " | " + esc(entry.tier) + " | " + esc(entry.section) +
        (surface ? " | " + surface : "") +
        (em ? " | " + em : "") +
        (entry.withdrawn && entry.reason ? " | " + esc(entry.reason) : "");

    if (linkToTournament) {
        var tGender = entry.gender || "";
        var tLink = encName(entry.tournament) + (tGender ? "|" + encName(tGender) : "");
        return '<a href="#/tournament/' + tLink + '" class="tournament-badge ' + cls + wdCls + '" title="' + title + '">' +
            esc(entry.tournament) + wdHTML + tierLabel + surfaceHTML + secHTML + '</a>';
    }
    return '<span class="tournament-badge ' + cls + wdCls + '" title="' + title + '">' +
        esc(entry.tournament) + wdHTML + tierLabel + surfaceHTML + secHTML + '</span>';
}

// === DASHBOARD VIEW ===
function renderDashboard() {
    var filtered = applyFilters(D.players);
    var container = document.getElementById("app");
    var countEl = document.getElementById("resultsCount");
    countEl.textContent = "Showing " + filtered.length.toLocaleString() + " player" + (filtered.length !== 1 ? "s" : "");

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">' +
            '<div class="empty-icon">🎾</div>' +
            '<div class="empty-title">No players found</div>' +
            '<div class="empty-text">Try adjusting your filters or search query</div>' +
            '<button class="empty-reset-btn" id="emptyResetBtn">Reset filters</button>' +
            '</div>';
        var resetBtn = document.getElementById("emptyResetBtn");
        if (resetBtn) resetBtn.addEventListener("click", resetFilters);
        return;
    }

    // Virtual scrolling: only render visible rows
    // Clean up previous scroll handler if any
    if (container._scrollHandler) {
        window.removeEventListener("scroll", container._scrollHandler);
        container._scrollHandler = null;
    }

    var CHUNK = 200;
    var total = filtered.length;
    var rendered = Math.min(CHUNK, total);

    var html = ['<div class="table-container"><table class="player-table"><thead><tr>'];
    html.push('<th class="rk-col">RK</th>');
    html.push('<th class="player-col">Player</th>');
    html.push('<th class="ctry-col">COUNTRY</th>');

    for (var wi = 0; wi < D.weeks.length; wi++) {
        var weekLabel = D.weeks[wi];
        var shortWeek = weekLabel.replace(/(\w{3})\s+(\d{1,2}).*/, function (m, mon, day) {
            return mon.toUpperCase() + " " + day;
        });
        html.push('<th class="week-col">' + esc(shortWeek) + '</th>');
    }
    html.push('</tr></thead><tbody>');

    for (var pi = 0; pi < rendered; pi++) {
        html.push(playerRowHTML(filtered[pi]));
    }

    html.push('</tbody></table></div>');
    container.innerHTML = html.join("");

    // Lazy-load remaining rows on scroll
    if (rendered < total) {
        // Add scroll indicator
        var indicator = document.createElement("div");
        indicator.className = "scroll-indicator";
        indicator.innerHTML = "&#8595; Scroll for more &middot; " + (total - rendered).toLocaleString() + " players remaining";
        container.appendChild(indicator);

        var loading = false;
        var onScroll = function () {
            if (loading || rendered >= total) return;
            var scrollBottom = window.innerHeight + window.scrollY;
            var docHeight = document.documentElement.scrollHeight;
            if (scrollBottom > docHeight - 600) {
                loading = true;
                var tbody = container.querySelector("tbody");
                var end = Math.min(rendered + CHUNK, total);
                var frag = document.createDocumentFragment();
                var tmp = document.createElement("tbody");
                var rows = [];
                for (var ri = rendered; ri < end; ri++) {
                    rows.push(playerRowHTML(filtered[ri]));
                }
                tmp.innerHTML = rows.join("");
                while (tmp.firstChild) {
                    frag.appendChild(tmp.firstChild);
                }
                tbody.appendChild(frag);
                rendered = end;
                loading = false;
                if (rendered >= total) {
                    window.removeEventListener("scroll", onScroll);
                    if (indicator.parentNode) indicator.parentNode.removeChild(indicator);
                } else {
                    indicator.innerHTML = "&#8595; Scroll for more &middot; " + (total - rendered).toLocaleString() + " players remaining";
                }
            }
        };
        window.addEventListener("scroll", onScroll);
        // Store for cleanup
        container._scrollHandler = onScroll;
    }
}

function playerRowHTML(p) {
    var hasEntries = p.entries.length > 0;
    var genderClass = p.gender === "Men" ? "gender-men" : "gender-women";
    var rowClass = genderClass + (hasEntries ? "" : " no-entries");
    var byWeek = entriesByWeek(p.entries);

    var html = '<tr class="' + rowClass + '">';
    html += '<td class="rk-cell">' + p.rank + '</td>';
    html += '<td class="player-cell"><a href="#/player/' + encName(p.name) + '">' + esc(p.name) + '</a></td>';
    html += '<td class="ctry-cell">' + esc(countryName(p.country)) + '</td>';

    for (var wi = 0; wi < D.weeks.length; wi++) {
        var wk = D.weeks[wi];
        var wEntries = byWeek[wk];
        html += '<td class="week-cell">';
        if (wEntries && wEntries.length > 0) {
            for (var ei = 0; ei < wEntries.length; ei++) {
                html += badgeHTML(wEntries[ei], true);
            }
        } else {
            html += '<span class="empty-dash">&mdash;</span>';
        }
        html += '</td>';
    }
    html += '</tr>';
    return html;
}

// === PLAYER PROFILE VIEW ===
function renderPlayerProfile(name) {
    var container = document.getElementById("app");
    var player = playerIndex[name.toLowerCase()];

    if (!player) {
        container.innerHTML = '<div class="profile-view"><div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + esc(name) + '</span></div><div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Player not found</div><div class="empty-text">' + esc(name) + ' was not found in the database</div></div></div>';
        return;
    }

    var genderClass = player.gender === "Men" ? "gender-men" : "gender-women";
    var genderTag = player.gender === "Men"
        ? '<span class="gender-tag men">ATP</span>'
        : '<span class="gender-tag women">WTA</span>';

    // Tier breakdown
    var tierCounts = {};
    var activeEntries = 0;
    var wdCount = 0;
    for (var i = 0; i < player.entries.length; i++) {
        var e = player.entries[i];
        if (e.withdrawn) { wdCount++; continue; }
        activeEntries++;
        var tier = e.tier || "Other";
        tierCounts[tier] = (tierCounts[tier] || 0) + 1;
    }

    var html = '<div class="profile-view">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + esc(player.name) + '</span></div>';

    // Header
    html += '<div class="profile-header ' + genderClass + '">';
    html += '<div class="profile-rank">#' + player.rank + '</div>';
    html += '<div class="profile-info">';
    html += '<div class="profile-name">' + esc(player.name) + '</div>';
    html += '<div class="profile-meta">';
    html += '<span class="profile-country">' + esc(player.country) + '</span>';
    html += genderTag;
    html += '</div></div></div>';

    // Stats cards
    html += '<div class="profile-stats">';
    html += '<div class="profile-stat-card"><div class="profile-stat-value">' + activeEntries + '</div><div class="profile-stat-label">Tournaments</div></div>';
    if (wdCount > 0) {
        html += '<div class="profile-stat-card"><div class="profile-stat-value">' + wdCount + '</div><div class="profile-stat-label">Withdrawn</div></div>';
    }
    var tierKeys = Object.keys(tierCounts);
    for (var ti = 0; ti < tierKeys.length; ti++) {
        html += '<div class="profile-stat-card"><div class="profile-stat-value">' + tierCounts[tierKeys[ti]] + '</div><div class="profile-stat-label">' + esc(tierKeys[ti]) + '</div></div>';
    }
    html += '</div>';

    // Schedule timeline
    if (player.entries.length > 0) {
        html += '<div class="schedule-section">';
        html += '<div class="section-title">Schedule Timeline</div>';
        html += '<div class="timeline">';

        var byWk = entriesByWeek(player.entries);
        for (var wi = 0; wi < D.weeks.length; wi++) {
            var wk = D.weeks[wi];
            var wEntries = byWk[wk];
            html += '<div class="timeline-week">';
            html += '<div class="timeline-week-label">' + esc(wk) + '</div>';
            if (wEntries && wEntries.length > 0) {
                for (var ei = 0; ei < wEntries.length; ei++) {
                    html += badgeHTML(wEntries[ei], true);
                }
            } else {
                html += '<div class="timeline-week-empty">&mdash;</div>';
            }
            html += '</div>';
        }
        html += '</div></div>';

        // Entry cards
        html += '<div class="schedule-section">';
        html += '<div class="section-title">All Entries</div>';
        html += '<div class="entry-cards">';
        for (var ci = 0; ci < player.entries.length; ci++) {
            var ce = player.entries[ci];
            html += '<div class="entry-card" data-tier="' + esc(ce.tier) + '">';
            html += '<div class="entry-card-info">';
            html += badgeHTML(ce, true);
            html += '<span class="entry-card-section">' + esc(ce.section) + '</span>';
            html += '<span class="entry-card-week">' + esc(ce.week) + '</span>';
            html += '</div>';
            if (ce.withdrawn && ce.reason) {
                html += '<span class="wd-reason">' + esc(ce.reason) + '</span>';
            }
            html += '</div>';
        }
        html += '</div></div>';
    } else {
        html += '<div class="empty-state">' +
            '<div class="empty-icon">📋</div>' +
            '<div class="empty-title">No upcoming entries</div>' +
            '<div class="empty-text">No tournament entries found for this player yet</div>' +
            '</div>';
    }

    html += '</div>';
    container.innerHTML = html;
    window.scrollTo(0, 0);
}

// === TOURNAMENT BROWSER VIEW ===
function renderTournamentBrowser() {
    var container = document.getElementById("app");

    // Collect all unique tiers
    var allTiers = {};
    var tournList = D.tournaments || [];
    for (var i = 0; i < tournList.length; i++) {
        if (tournList[i].tier && tournList[i].tier !== "ITF") allTiers[tournList[i].tier] = true;
    }
    var tierOrder = [
        "Grand Slam", "ATP 1000", "WTA 1000", "ATP 500", "WTA 500",
        "ATP 250", "WTA 250", "ATP", "WTA",
        "ATP Challenger 175", "ATP Challenger 125", "ATP Challenger 100",
        "ATP Challenger 75", "ATP Challenger 50", "ATP Challenger",
        "WTA 125"
    ];
    var tierRank = {};
    for (var oi = 0; oi < tierOrder.length; oi++) tierRank[tierOrder[oi]] = oi;
    var tierList = Object.keys(allTiers).sort(function (a, b) {
        var ra = tierRank[a] !== undefined ? tierRank[a] : 99;
        var rb = tierRank[b] !== undefined ? tierRank[b] : 99;
        return ra - rb;
    });

    // Filter tournaments (ITF tournaments are on a separate page)
    var filtered = [];
    for (var i = 0; i < tournList.length; i++) {
        var t = tournList[i];
        if (t.tier === "ITF") continue;
        if (state.tournamentTierFilter === "challenger-125") {
            // Special filter: show only Challenger + WTA 125
            var tl = (t.tier || "").toLowerCase();
            if (tl.indexOf("challenger") === -1 && tl.indexOf("125") === -1) continue;
        } else if (state.tournamentTierFilter !== "all" && t.tier !== state.tournamentTierFilter) {
            continue;
        }
        filtered.push(t);
    }

    // Group by week
    var weekGroups = {};
    var weekOrder = [];
    for (var i = 0; i < filtered.length; i++) {
        var wk = filtered[i].week || "TBD";
        if (!weekGroups[wk]) { weekGroups[wk] = []; weekOrder.push(wk); }
        weekGroups[wk].push(filtered[i]);
    }

    var isEntryListsView = state.tournamentTierFilter === "challenger-125";
    var viewTitle = isEntryListsView ? "Entry Lists" : "Tournaments";

    var html = '<div class="tournaments-view">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + viewTitle + '</span></div>';
    html += '<div class="section-title">' + viewTitle + ' (' + filtered.length + ')</div>';

    // Tier filter buttons
    html += '<div class="tier-filters">';
    if (isEntryListsView) {
        // Entry Lists view: show "All" as active (meaning all Challenger+125)
        html += '<button class="tier-btn active" data-tier="challenger-125">All</button>';
        // Also add individual tier buttons for the filtered tiers
        for (var ti = 0; ti < tierList.length; ti++) {
            var tl = tierList[ti].toLowerCase();
            if (tl.indexOf("challenger") !== -1 || tl.indexOf("125") !== -1) {
                html += '<button class="tier-btn" data-tier="' + esc(tierList[ti]) + '">' + esc(tierList[ti]) + '</button>';
            }
        }
    } else {
        html += '<button class="tier-btn' + (state.tournamentTierFilter === "all" ? " active" : "") + '" data-tier="all">All</button>';
        for (var ti = 0; ti < tierList.length; ti++) {
            var isActive = state.tournamentTierFilter === tierList[ti] ? " active" : "";
            html += '<button class="tier-btn' + isActive + '" data-tier="' + esc(tierList[ti]) + '">' + esc(tierList[ti]) + '</button>';
        }
    }
    html += '</div>';

    // Week groups
    for (var wi = 0; wi < weekOrder.length; wi++) {
        var wk = weekOrder[wi];
        var group = weekGroups[wk];
        group.sort(function (a, b) {
            var ra = tierRank[a.tier] !== undefined ? tierRank[a.tier] : 99;
            var rb = tierRank[b.tier] !== undefined ? tierRank[b.tier] : 99;
            return ra - rb;
        });
        html += '<div class="week-group">';
        html += '<div class="week-group-header">' + esc(wk) + '</div>';
        html += '<div class="tournament-grid">';
        for (var gi = 0; gi < group.length; gi++) {
            var t = group[gi];
            var tCardLink = encName(t.name) + (t.gender ? "|" + encName(t.gender) : "");
            html += '<a href="#/tournament/' + tCardLink + '" class="tournament-card">';
            html += '<div class="tournament-card-top">';
            html += '<span class="tournament-card-tier ' + getTierColorClass(t.tier) + '">' + esc(t.tier) + '</span>';
            if (t.surface) {
                var sfcCls = "sfc-" + t.surface.toLowerCase();
                html += '<span class="tournament-card-surface ' + sfcCls + '">' + esc(t.surface) + '</span>';
            }
            html += '</div>';
            html += '<div class="tournament-card-name">' + esc(t.name) + '</div>';
            if (t.city) {
                html += '<div class="tournament-card-location">' + esc(t.city) + (t.country ? ', ' + esc(t.country) : '') + '</div>';
            }
            html += '<div class="tournament-card-meta">';
            if (t.dates) {
                html += '<span class="tournament-card-dates">' + esc(t.dates) + '</span>';
            }
            html += '<span class="tournament-card-players">' + t.playerCount + ' players</span>';
            html += '</div></a>';
        }
        html += '</div></div>';
    }

    if (filtered.length === 0) {
        html += '<div class="empty-state">' +
            '<div class="empty-icon">🏟️</div>' +
            '<div class="empty-title">No tournaments found</div>' +
            '<div class="empty-text">Try selecting a different tier filter</div>' +
            '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Wire up tier filter buttons
    var tierBtns = container.querySelectorAll(".tier-btn");
    for (var i = 0; i < tierBtns.length; i++) {
        tierBtns[i].addEventListener("click", function () {
            state.tournamentTierFilter = this.getAttribute("data-tier");
            renderTournamentBrowser();
        });
    }

    window.scrollTo(0, 0);
}

// === ITF BROWSER VIEW ===
function buildItfKey(t) {
    return (t.city || "").toLowerCase() + "|" +
           (t.tier || "").toLowerCase() + "|" +
           (t.gender || "").toLowerCase() + "|" +
           (t.week || "").toLowerCase();
}

function renderITFBrowser() {
    var container = document.getElementById("app");
    var itfData = (window.ITF_DATA && window.ITF_DATA.itfTournaments) || [];
    var itfEntries = (window.ITF_DATA && window.ITF_DATA.itfEntries) || {};

    if (!itfData.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎾</div><div class="empty-title">No ITF calendar data</div></div>';
        return;
    }

    // State for gender and tier filter
    if (!state.itfGender) state.itfGender = "all";
    if (!state.itfTierFilter) state.itfTierFilter = "all";

    // Filter by gender
    var filtered = [];
    for (var i = 0; i < itfData.length; i++) {
        var t = itfData[i];
        if (state.itfGender !== "all" && t.gender !== state.itfGender) continue;
        if (state.itfTierFilter !== "all" && t.tier !== state.itfTierFilter) continue;
        filtered.push(t);
    }

    // Collect unique tiers for filter buttons
    var allTiers = {};
    for (var i = 0; i < itfData.length; i++) {
        var t = itfData[i];
        if (state.itfGender !== "all" && t.gender !== state.itfGender) continue;
        if (t.tier) allTiers[t.tier] = true;
    }
    var tierOrder = [
        "ITF M25", "ITF M15",
        "ITF W100", "ITF W75", "ITF W50", "ITF W35", "ITF W15"
    ];
    var tierRank = {};
    for (var oi = 0; oi < tierOrder.length; oi++) tierRank[tierOrder[oi]] = oi;
    var tierList = Object.keys(allTiers).sort(function(a, b) {
        var ra = tierRank[a] !== undefined ? tierRank[a] : 99;
        var rb = tierRank[b] !== undefined ? tierRank[b] : 99;
        return ra - rb;
    });

    var html = '<div class="tournament-browser">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><span class="bc-current">ITF Calendar</span></div>';
    html += '<h2 class="section-title">ITF Calendar (' + filtered.length + ')</h2>';

    // Gender tabs
    html += '<div class="itf-gender-tabs">';
    html += '<button class="tier-btn' + (state.itfGender === "all" ? " active" : "") + '" data-itfgender="all">All</button>';
    html += '<button class="tier-btn' + (state.itfGender === "Men" ? " active" : "") + '" data-itfgender="Men" style="' + (state.itfGender === "Men" ? "border-color:#4da6ff;color:#4da6ff;background:rgba(77,166,255,0.08)" : "") + '">Men\'s ITF</button>';
    html += '<button class="tier-btn' + (state.itfGender === "Women" ? " active" : "") + '" data-itfgender="Women" style="' + (state.itfGender === "Women" ? "border-color:#ff6b9d;color:#ff6b9d;background:rgba(255,107,157,0.08)" : "") + '">Women\'s ITF</button>';
    html += '</div>';

    // Tier filter buttons
    html += '<div class="tier-filters">';
    html += '<button class="tier-btn' + (state.itfTierFilter === "all" ? " active" : "") + '" data-itftier="all">All Tiers</button>';
    for (var ti = 0; ti < tierList.length; ti++) {
        var isActive = state.itfTierFilter === tierList[ti];
        html += '<button class="tier-btn' + (isActive ? " active" : "") + '" data-itftier="' + esc(tierList[ti]) + '">' + esc(tierList[ti]) + '</button>';
    }
    html += '</div>';

    // Group by week
    var weekGroups = {};
    var weekOrder = [];
    for (var i = 0; i < filtered.length; i++) {
        var wk = filtered[i].week || "TBD";
        if (!weekGroups[wk]) { weekGroups[wk] = []; weekOrder.push(wk); }
        weekGroups[wk].push(filtered[i]);
    }

    // Render week groups
    for (var wi = 0; wi < weekOrder.length; wi++) {
        var wk = weekOrder[wi];
        var tourns = weekGroups[wk];
        // Use dates from first tournament as group header
        var weekLabel = tourns[0].dates || wk;
        html += '<div class="week-group">';
        html += '<div class="week-header">' + esc(weekLabel) + '</div>';
        html += '<div class="tournament-grid">';
        for (var ti = 0; ti < tourns.length; ti++) {
            var t = tourns[ti];
            var sfcClass = "sfc-" + (t.surface || "").toLowerCase().replace(/ *\(i\)/, "").replace("carpet", "hard");
            var entryKey = buildItfKey(t);
            var hasEntries = !!itfEntries[entryKey];
            var playerCount = hasEntries ? itfEntries[entryKey].players.length : 0;

            if (hasEntries) {
                html += '<a href="#/itf-tournament/' + encName(entryKey) + '" class="tournament-card">';
            } else {
                html += '<div class="tournament-card">';
            }
            html += '<div class="tournament-card-top">';
            html += '<span class="tournament-card-tier ' + getTierColorClass(t.tier) + '">' + esc(t.tier) + '</span>';
            if (t.surface) html += '<span class="tournament-card-surface ' + sfcClass + '">' + esc(t.surface) + '</span>';
            html += '</div>';
            html += '<div class="tournament-card-name">' + esc(t.city) + '</div>';
            html += '<div class="tournament-card-meta">';
            if (t.dates) html += '<span class="tournament-card-dates">' + esc(t.dates) + '</span>';
            if (hasEntries) {
                html += '<span class="tournament-card-players">' + playerCount + ' players</span>';
            } else {
                html += '<span class="tournament-card-players">' + esc(t.gender) + '</span>';
            }
            html += '</div>';
            html += hasEntries ? '</a>' : '</div>';
        }
        html += '</div></div>';
    }

    if (filtered.length === 0) {
        html += '<div class="empty-state">' +
            '<div class="empty-icon">🎾</div>' +
            '<div class="empty-title">No ITF tournaments found</div>' +
            '<div class="empty-text">Try selecting a different filter</div>' +
            '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Wire up gender filter buttons
    var genderBtns = container.querySelectorAll("[data-itfgender]");
    for (var i = 0; i < genderBtns.length; i++) {
        genderBtns[i].addEventListener("click", function() {
            state.itfGender = this.getAttribute("data-itfgender");
            state.itfTierFilter = "all";
            renderITFBrowser();
        });
    }

    // Wire up tier filter buttons
    var tierBtns = container.querySelectorAll("[data-itftier]");
    for (var i = 0; i < tierBtns.length; i++) {
        tierBtns[i].addEventListener("click", function() {
            state.itfTierFilter = this.getAttribute("data-itftier");
            renderITFBrowser();
        });
    }

    window.scrollTo(0, 0);
}

// === ITF TOURNAMENT DETAIL VIEW ===
function renderITFTournamentDetail(key) {
    var container = document.getElementById("app");
    var itfEntries = (window.ITF_DATA && window.ITF_DATA.itfEntries) || {};
    var tourn = itfEntries[key];

    if (!tourn) {
        container.innerHTML = '<div class="tournament-detail-view"><div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><a href="#/itf">ITF</a><span class="bc-sep">&#9656;</span><span class="bc-current">Not Found</span></div><div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Tournament not found</div><div class="empty-text">This ITF tournament was not found in the database</div></div></div>';
        return;
    }

    // Build section list from players
    var sectionOrder = {"Main Draw": 0, "Qualifying": 1, "Alternates": 2};
    var sections = {};
    var activeEntries = [];
    var wdEntries = [];
    for (var i = 0; i < tourn.players.length; i++) {
        var p = tourn.players[i];
        sections[p.s] = true;
        if (p.w) wdEntries.push(p);
        else activeEntries.push(p);
    }
    var sectionList = Object.keys(sections).sort(function(a, b) {
        var oa = sectionOrder[a] !== undefined ? sectionOrder[a] : 9;
        var ob = sectionOrder[b] !== undefined ? sectionOrder[b] : 9;
        return oa - ob;
    });

    if (!state.itfSection) state.itfSection = "all";
    var currentSection = state.itfSection;
    if (currentSection !== "all" && !sections[currentSection]) currentSection = "all";

    // Filter by section
    var entries = activeEntries;
    if (currentSection !== "all") {
        entries = entries.filter(function(e) { return e.s === currentSection; });
    }

    var genderClass = tourn.gender === "Men" ? "gender-men" : "gender-women";
    var genderTag = tourn.gender === "Men"
        ? '<span class="gender-tag men">ATP</span>'
        : '<span class="gender-tag women">WTA</span>';

    var html = '<div class="tournament-detail-view">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><a href="#/itf">ITF</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + esc(tourn.name) + '</span></div>';

    // Header
    html += '<div class="tournament-header">';
    html += '<div>';
    html += '<div class="tournament-title">' + esc(tourn.name) + '</div>';
    html += '<div class="tournament-meta">';
    html += '<span class="tournament-card-tier ' + getTierColorClass(tourn.tier) + '">' + esc(tourn.tier) + '</span>';
    html += genderTag;
    if (tourn.dates) html += '<span class="tournament-week-label">' + esc(tourn.dates) + '</span>';
    html += '<span class="tournament-player-count">' + activeEntries.length + ' players</span>';
    html += '</div></div></div>';

    // Section tabs
    if (sectionList.length > 1) {
        html += '<div class="section-tabs">';
        html += '<button class="section-tab' + (currentSection === "all" ? " active" : "") + '" data-itfsec="all">All (' + activeEntries.length + ')</button>';
        for (var si = 0; si < sectionList.length; si++) {
            var sec = sectionList[si];
            var secCount = activeEntries.filter(function(e) { return e.s === sec; }).length;
            if (secCount === 0) continue;
            html += '<button class="section-tab' + (currentSection === sec ? " active" : "") + '" data-itfsec="' + esc(sec) + '">' + esc(sec) + ' (' + secCount + ')</button>';
        }
        html += '</div>';
    }

    // Entry table
    html += '<table class="entry-table"><thead><tr>';
    html += '<th>Rank</th><th>Player</th><th>Country</th><th>Section</th>';
    html += '</tr></thead><tbody>';

    for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        html += '<tr>';
        html += '<td class="rank-col">' + (e.r > 0 ? e.r : "—") + '</td>';
        html += '<td class="player-col">' + esc(e.n) + '</td>';
        html += '<td class="ctry-col">' + esc(e.c) + '</td>';
        html += '<td>' + esc(e.s) + '</td>';
        html += '</tr>';
    }
    html += '</tbody></table>';

    if (entries.length === 0) {
        html += '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">No entries in this section</div></div>';
    }

    // Withdrawals
    if (wdEntries.length > 0) {
        html += '<div class="section-title" style="margin-top:24px">Withdrawals (' + wdEntries.length + ')</div>';
        html += '<table class="entry-table"><thead><tr>';
        html += '<th>Rank</th><th>Player</th><th>Country</th><th>Section</th>';
        html += '</tr></thead><tbody>';
        for (var wi = 0; wi < wdEntries.length; wi++) {
            var w = wdEntries[wi];
            html += '<tr class="withdrawn-row">';
            html += '<td class="rank-col">' + (w.r > 0 ? w.r : "—") + '</td>';
            html += '<td class="player-col">' + esc(w.n) + ' <span class="wd-tag">WD</span></td>';
            html += '<td class="ctry-col">' + esc(w.c) + '</td>';
            html += '<td>' + esc(w.s) + '</td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Wire up section tabs
    var secBtns = container.querySelectorAll("[data-itfsec]");
    for (var i = 0; i < secBtns.length; i++) {
        secBtns[i].addEventListener("click", function() {
            state.itfSection = this.getAttribute("data-itfsec");
            renderITFTournamentDetail(key);
        });
    }

    window.scrollTo(0, 0);
}

// === TOURNAMENT DETAIL VIEW ===
function renderTournamentDetail(name, gender) {
    var container = document.getElementById("app");
    var key = name.toLowerCase() + (gender ? "|" + gender.toLowerCase() : "");
    var tourn = tournamentEntries[key];
    // Fallback: try without gender for backward compat with old URLs
    if (!tourn && gender) {
        tourn = tournamentEntries[name.toLowerCase()];
    }
    if (!tourn && !gender) {
        // Try to find by name prefix (matches first gender variant)
        var prefix = name.toLowerCase() + "|";
        var allKeys = Object.keys(tournamentEntries);
        for (var ki = 0; ki < allKeys.length; ki++) {
            if (allKeys[ki].indexOf(prefix) === 0) {
                tourn = tournamentEntries[allKeys[ki]];
                break;
            }
        }
    }

    if (!tourn) {
        container.innerHTML = '<div class="tournament-detail-view"><div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><a href="#/tournaments">Tournaments</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + esc(name) + '</span></div><div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Tournament not found</div><div class="empty-text">' + esc(name) + ' was not found in the database</div></div></div>';
        return;
    }

    var sectionOrder = {"Main Draw": 0, "Qualifying": 1, "Alternates": 2};
    var sections = Object.keys(tourn.sections).sort(function (a, b) {
        var oa = sectionOrder[a] !== undefined ? sectionOrder[a] : 9;
        var ob = sectionOrder[b] !== undefined ? sectionOrder[b] : 9;
        return oa - ob;
    });
    var currentSection = state.tournamentSection;
    if (currentSection !== "all" && !tourn.sections[currentSection]) {
        currentSection = "all";
    }

    // Split entries into active and withdrawn
    var activeEntries = [];
    var wdEntries = [];
    for (var ai = 0; ai < tourn.entries.length; ai++) {
        if (tourn.entries[ai].withdrawn) wdEntries.push(tourn.entries[ai]);
        else activeEntries.push(tourn.entries[ai]);
    }

    // Filter active entries by section
    var entries = activeEntries;
    if (currentSection !== "all") {
        entries = entries.filter(function (e) { return e.section === currentSection; });
    }

    var html = '<div class="tournament-detail-view">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><a href="#/tournaments">Tournaments</a><span class="bc-sep">&#9656;</span><span class="bc-current">' + esc(tourn.name) + '</span></div>';

    // Find calendar metadata from D.tournaments (match by name + gender)
    var tournMeta = null;
    var _tournGender = (tourn.gender || "").toLowerCase();
    for (var mi = 0; mi < (D.tournaments || []).length; mi++) {
        var _tm = D.tournaments[mi];
        var _tmGender = (_tm.gender || "").toLowerCase();
        if (_tm.name.toLowerCase() === name.toLowerCase() && (!_tournGender || !_tmGender || _tournGender === _tmGender)) {
            tournMeta = _tm;
            break;
        }
    }

    // Header
    html += '<div class="tournament-header">';
    html += '<div>';
    html += '<div class="tournament-title">' + esc(tourn.name) + '</div>';
    if (tournMeta && tournMeta.city) {
        html += '<div class="tournament-location">' + esc(tournMeta.city) + (tournMeta.country ? ', ' + esc(tournMeta.country) : '') + '</div>';
    }
    html += '<div class="tournament-meta">';
    html += '<span class="tournament-card-tier ' + getTierColorClass(tourn.tier) + '">' + esc(tourn.tier) + '</span>';
    if (tournMeta && tournMeta.surface) {
        var sfcCls = "sfc-" + tournMeta.surface.toLowerCase();
        html += '<span class="tournament-card-surface ' + sfcCls + '">' + esc(tournMeta.surface) + '</span>';
    }
    if (tourn.hasFullList) html += '<span class="full-list-badge">Full Entry List</span>';
    if (tournMeta && tournMeta.dates) {
        html += '<span class="tournament-week-label">' + esc(tournMeta.dates) + '</span>';
    } else {
        html += '<span class="tournament-week-label">' + esc(tourn.week) + '</span>';
    }
    html += '<span class="tournament-player-count">' + activeEntries.length + ' players</span>';
    html += '</div></div></div>';

    // Section tabs (counts based on active entries only)
    if (sections.length > 1) {
        html += '<div class="section-tabs">';
        html += '<button class="section-tab' + (currentSection === "all" ? " active" : "") + '" data-section="all">All (' + activeEntries.length + ')</button>';
        for (var si = 0; si < sections.length; si++) {
            var sec = sections[si];
            var secCount = activeEntries.filter(function (e) { return e.section === sec; }).length;
            if (secCount === 0) continue;
            html += '<button class="section-tab' + (currentSection === sec ? " active" : "") + '" data-section="' + esc(sec) + '">' + esc(sec) + ' (' + secCount + ')</button>';
        }
        html += '</div>';
    }

    // Entry table (active players only)
    html += '<table class="entry-table"><thead><tr>';
    html += '<th>Rank</th><th>Player</th><th>Country</th><th>Section</th>';
    html += '</tr></thead><tbody>';

    for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        var isRanked = !!playerIndex[e.name.toLowerCase()];
        var rowClass = (!isRanked && tourn.hasFullList) ? "unranked-row" : "";
        html += '<tr class="' + rowClass + '">';
        html += '<td class="rank-col">' + (e.rank || "—") + '</td>';
        if (isRanked) {
            html += '<td class="player-col"><a href="#/player/' + encName(e.name) + '">' + esc(e.name) + '</a></td>';
        } else {
            html += '<td class="player-col">' + esc(e.name) + '</td>';
        }
        html += '<td class="ctry-col">' + esc(e.country) + '</td>';
        var secText = esc(e.section);
        if (e.entry_method) secText += ' <span class="entry-method-indicator" style="display:inline">' + esc(e.entry_method) + '</span>';
        html += '<td>' + secText + '</td>';
        html += '</tr>';
    }

    html += '</tbody></table>';

    if (entries.length === 0) {
        html += '<div class="empty-state">' +
            '<div class="empty-icon">📋</div>' +
            '<div class="empty-title">No entries in this section</div>' +
            '<div class="empty-text">Try selecting a different section filter</div>' +
            '</div>';
    }

    // Withdrawals section (separate from entry list)
    if (wdEntries.length > 0) {
        html += '<div class="section-title" style="margin-top:24px">Withdrawals (' + wdEntries.length + ')</div>';
        html += '<table class="entry-table"><thead><tr>';
        html += '<th>Rank</th><th>Player</th><th>Country</th><th>Section</th>';
        html += '</tr></thead><tbody>';
        for (var wi = 0; wi < wdEntries.length; wi++) {
            var w = wdEntries[wi];
            var isRankedW = !!playerIndex[w.name.toLowerCase()];
            html += '<tr class="withdrawn-row">';
            html += '<td class="rank-col">' + (w.rank || "—") + '</td>';
            if (isRankedW) {
                html += '<td class="player-col"><a href="#/player/' + encName(w.name) + '">' + esc(w.name) + '</a>';
            } else {
                html += '<td class="player-col">' + esc(w.name);
            }
            var isRet = w.withdrawal_type === "RET";
            html += isRet ? ' <span class="ret-tag">RET</span>' : ' <span class="wd-tag">WD</span>';
            if (w.reason) html += ' <span class="wd-reason-inline">' + esc(w.reason) + '</span>';
            html += '</td>';
            html += '<td class="ctry-col">' + esc(w.country) + '</td>';
            html += '<td>' + esc(w.section) + '</td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Wire up section tabs
    var secBtns = container.querySelectorAll(".section-tab");
    for (var i = 0; i < secBtns.length; i++) {
        secBtns[i].addEventListener("click", function () {
            state.tournamentSection = this.getAttribute("data-section");
            renderTournamentDetail(name);
        });
    }

    window.scrollTo(0, 0);
}

// === WITHDRAWALS VIEW ===
function renderWithdrawals() {
    var container = document.getElementById("app");

    // Collect all withdrawn entries across all players
    var withdrawals = [];
    for (var pi = 0; pi < D.players.length; pi++) {
        var player = D.players[pi];
        for (var ei = 0; ei < player.entries.length; ei++) {
            var e = player.entries[ei];
            if (!e.withdrawn) continue;
            withdrawals.push({
                playerName: player.name,
                playerRank: player.rank,
                playerCountry: player.country,
                playerGender: player.gender,
                tournament: e.tournament,
                tier: e.tier,
                section: e.section,
                week: e.week,
                source: e.source,
                reason: e.reason || "",
                withdrawal_type: e.withdrawal_type || "",
            });
        }
    }

    // Sort by gender (Men first), then by rank within each gender
    withdrawals.sort(function (a, b) {
        if (a.playerGender !== b.playerGender) {
            return a.playerGender === "Men" ? -1 : 1;
        }
        return a.playerRank - b.playerRank;
    });

    // Gender filter
    var genderFilter = "all";
    var html = '<div class="withdrawals-view">';
    html += '<div class="breadcrumbs"><a href="#/">Dashboard</a><span class="bc-sep">&#9656;</span><span class="bc-current">Withdrawals</span></div>';
    // Count unique players
    var uniqueWdPlayers = {};
    for (var i = 0; i < withdrawals.length; i++) {
        uniqueWdPlayers[withdrawals[i].playerName] = true;
    }
    var uniqueWdCount = Object.keys(uniqueWdPlayers).length;
    html += '<div class="section-title">Withdrawals (' + uniqueWdCount + ' players)</div>';

    // Gender filter buttons
    html += '<div class="wd-filters">';
    html += '<button class="tier-btn active" data-wdgender="all">All</button>';
    html += '<button class="tier-btn" data-wdgender="Men">ATP</button>';
    html += '<button class="tier-btn" data-wdgender="Women">WTA</button>';
    html += '</div>';

    if (withdrawals.length === 0) {
        html += '<div class="empty-state">';
        html += '<div class="empty-icon">&#10003;</div>';
        html += '<div class="empty-title">No withdrawals</div>';
        html += '<div class="empty-text">No players have withdrawn from upcoming tournaments yet</div>';
        html += '</div>';
    } else {
        // Group by week, then within each week split by gender
        var weekGroups = {};
        var weekOrder = [];
        for (var i = 0; i < withdrawals.length; i++) {
            var wk = withdrawals[i].week || "TBD";
            if (!weekGroups[wk]) { weekGroups[wk] = []; weekOrder.push(wk); }
            weekGroups[wk].push(withdrawals[i]);
        }

        html += '<div id="wdList">';
        for (var wi = 0; wi < weekOrder.length; wi++) {
            var wk = weekOrder[wi];
            var group = weekGroups[wk];
            html += '<div class="week-group wd-week-group">';
            html += '<div class="week-group-header">' + esc(wk) + '</div>';

            // Split into ATP and WTA within each week
            var menWd = [];
            var womenWd = [];
            for (var gi = 0; gi < group.length; gi++) {
                if (group[gi].playerGender === "Men") menWd.push(group[gi]);
                else womenWd.push(group[gi]);
            }

            var genderSections = [];
            if (menWd.length > 0) genderSections.push({ label: "ATP", items: menWd });
            if (womenWd.length > 0) genderSections.push({ label: "WTA", items: womenWd });

            for (var gsi = 0; gsi < genderSections.length; gsi++) {
                var gs = genderSections[gsi];
                // Group by player name to avoid repeating the same player
                var playerGroups = [];
                var playerGroupMap = {};
                for (var gi = 0; gi < gs.items.length; gi++) {
                    var w = gs.items[gi];
                    var pkey = w.playerName;
                    if (!playerGroupMap[pkey]) {
                        playerGroupMap[pkey] = { player: w, tournaments: [] };
                        playerGroups.push(playerGroupMap[pkey]);
                    }
                    playerGroupMap[pkey].tournaments.push(w);
                }
                html += '<div class="wd-gender-header" data-gender="' + (gs.label === "ATP" ? "Men" : "Women") + '">' + gs.label + ' (' + playerGroups.length + ')</div>';
                html += '<div class="wd-feed">';
                for (var pi = 0; pi < playerGroups.length; pi++) {
                    var pg = playerGroups[pi];
                    var w = pg.player;
                    var genderCls = w.playerGender === "Men" ? "wd-men" : "wd-women";
                    html += '<div class="wd-feed-card ' + genderCls + '" data-gender="' + esc(w.playerGender) + '">';
                    html += '<div class="wd-player-info">';
                    html += '<span class="wd-rank">#' + w.playerRank + '</span>';
                    html += '<a href="#/player/' + encName(w.playerName) + '" class="wd-player-name">' + esc(w.playerName) + '</a>';
                    html += '<span class="wd-country">' + esc(w.playerCountry) + '</span>';
                    html += '</div>';
                    html += '<div class="wd-tournament-list">';
                    for (var ti = 0; ti < pg.tournaments.length; ti++) {
                        var t = pg.tournaments[ti];
                        html += '<div class="wd-tournament-info">';
                        var wdTLink = encName(t.tournament) + (t.playerGender ? "|" + encName(t.playerGender) : "");
                        html += '<a href="#/tournament/' + wdTLink + '" class="tournament-badge ' + getBadgeClass(t.tier) + '">' + esc(t.tournament) + '</a>';
                        var sec = shortSection(t.section);
                        if (sec) html += '<span class="wd-section">' + sec + '</span>';
                        if (t.withdrawal_type === "RET") {
                            html += '<span class="ret-tag">RET</span>';
                        }
                        if (t.reason) html += '<span class="wd-reason">' + esc(t.reason) + '</span>';
                        html += '</div>';
                    }
                    html += '</div>';
                    html += '</div>';
                }
                html += '</div>';
            }
            html += '</div>';
        }
        html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Wire up gender filter
    var filterBtns = container.querySelectorAll("[data-wdgender]");
    for (var i = 0; i < filterBtns.length; i++) {
        filterBtns[i].addEventListener("click", function () {
            for (var j = 0; j < filterBtns.length; j++) filterBtns[j].classList.remove("active");
            this.classList.add("active");
            var g = this.getAttribute("data-wdgender");
            var cards = container.querySelectorAll(".wd-feed-card");
            for (var k = 0; k < cards.length; k++) {
                if (g === "all" || cards[k].getAttribute("data-gender") === g) {
                    cards[k].style.display = "";
                } else {
                    cards[k].style.display = "none";
                }
            }
            // Also hide/show gender sub-headers
            var gHeaders = container.querySelectorAll(".wd-gender-header");
            for (var k = 0; k < gHeaders.length; k++) {
                if (g === "all" || gHeaders[k].getAttribute("data-gender") === g) {
                    gHeaders[k].style.display = "";
                } else {
                    gHeaders[k].style.display = "none";
                }
            }
        });
    }

    window.scrollTo(0, 0);
}

// === EVENT LISTENERS ===
var debounceTimer = null;

function setupListeners() {
    // Search
    var searchInput = document.getElementById("searchInput");
    searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        var val = this.value.trim();
        debounceTimer = setTimeout(function () {
            state.search = val;
            if (state.currentView === "dashboard") renderDashboard();
        }, 150);
    });

    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            this.value = "";
            state.search = "";
            if (state.currentView === "dashboard") renderDashboard();
        }
    });

    // Gender tabs
    var genderBtns = document.querySelectorAll(".gender-tabs button");
    for (var i = 0; i < genderBtns.length; i++) {
        genderBtns[i].addEventListener("click", function () {
            for (var j = 0; j < genderBtns.length; j++) genderBtns[j].classList.remove("active");
            this.classList.add("active");
            state.gender = this.getAttribute("data-gender");
            if (state.currentView === "dashboard") renderDashboard();
        });
    }

    // Entries only toggle
    document.getElementById("entriesOnly").addEventListener("change", function () {
        state.entriesOnly = this.checked;
        if (state.currentView === "dashboard") renderDashboard();
    });

    // Rank filter
    var rankMin = document.getElementById("rankMin");
    var rankMax = document.getElementById("rankMax");

    rankMin.addEventListener("change", function () {
        var val = parseInt(this.value) || 1;
        state.rankMin = Math.max(1, val);
        if (state.currentView === "dashboard") renderDashboard();
    });

    rankMax.addEventListener("change", function () {
        var val = parseInt(this.value) || 1500;
        state.rankMax = Math.min(1500, val);
        if (state.currentView === "dashboard") renderDashboard();
    });

    // Keyboard shortcut: / to focus search
    document.addEventListener("keydown", function (e) {
        if (e.key === "/" && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
        }
    });

    // Hash router
    window.addEventListener("hashchange", route);
}

// === INIT ===
document.addEventListener("DOMContentLoaded", function () {
    renderStats();
    setupListeners();
    route();
});

})();
