/* ═══════════════════════════════════════════════════════════════════════
   Arena — Application Script
   Extracted from templates/index.html
   Server config is read from window.__ARENA_CONFIG (set by template).
   ═══════════════════════════════════════════════════════════════════════ */

// Global error catcher for mobile debugging
window.onerror = function(message, source, lineno, colno, error) {
    const errorMsg = `JS Error: ${message} at ${source}:${lineno}:${colno}`;
    console.error(errorMsg);
    if (typeof showDebugToast === 'function') {
        showDebugToast(errorMsg);
    } else {
        setTimeout(() => {
            if (typeof showDebugToast === 'function') showDebugToast(errorMsg);
        }, 1000);
    }
    return false;
};
window.addEventListener('unhandledrejection', function(event) {
    const errorMsg = `Unhandled Promise Rejection: ${event.reason}`;
    console.error(errorMsg);
    if (typeof showDebugToast === 'function') {
        showDebugToast(errorMsg);
    } else {
        setTimeout(() => {
            if (typeof showDebugToast === 'function') showDebugToast(errorMsg);
        }, 1000);
    }
});

// ── Arena: Tamriel Map Modal ──────────────────────────────────────────────
let cachedProvincesData = null;
let selectedProvinceName = null;

const PROVINCE_MAP_COORDS = {
    "High Rock": {
        "pinX": 144.0,
        "pinY": 255.0,
        "cap": "Daggerfall",
        "path": "M 317,78 L 326,84 L 329,92 L 334,94 L 336,101 L 344,106 L 346,104 L 343,98 L 345,87 L 349,83 L 360,88 L 362,87 L 362,89 L 366,91 L 366,99 L 382,113 L 387,111 L 385,107 L 392,103 L 398,95 L 409,93 L 414,87 L 419,90 L 420,107 L 405,119 L 390,138 L 387,173 L 381,180 L 367,184 L 347,183 L 341,186 L 327,185 L 324,192 L 313,200 L 312,209 L 309,210 L 307,216 L 299,222 L 294,232 L 274,232 L 272,238 L 260,248 L 233,256 L 230,259 L 215,259 L 205,253 L 200,257 L 201,259 L 142,259 L 137,265 L 138,268 L 135,274 L 127,280 L 121,301 L 116,304 L 102,306 L 98,304 L 95,299 L 101,293 L 113,291 L 115,289 L 112,287 L 101,286 L 100,290 L 94,293 L 87,291 L 86,274 L 93,271 L 94,264 L 98,265 L 103,261 L 103,259 L 96,254 L 98,240 L 95,237 L 97,235 L 90,226 L 94,222 L 100,222 L 102,220 L 101,218 L 107,217 L 110,212 L 120,208 L 127,202 L 137,200 L 144,195 L 142,186 L 145,185 L 150,173 L 168,151 L 169,148 L 164,140 L 168,135 L 176,132 L 179,121 L 186,114 L 197,109 L 207,113 L 210,112 L 216,101 L 227,94 L 232,97 L 243,93 L 252,94 L 257,99 L 255,107 L 257,111 L 253,118 L 255,120 L 255,131 L 251,144 L 255,157 L 260,158 L 266,155 L 272,146 L 275,147 L 273,144 L 279,136 L 290,132 L 288,129 L 290,122 L 295,120 L 299,123 L 304,119 L 303,113 L 306,111 L 302,104 L 306,100 L 312,100 L 308,88 L 316,79 Z"
    },
    "Skyrim": {
        "pinX": 570.0,
        "pinY": 115.0,
        "cap": "Solitude",
        "path": "M 450,81 L 460,82 L 461,84 L 460,89 L 463,92 L 460,95 L 459,106 L 457,109 L 452,110 L 446,117 L 432,120 L 428,124 L 427,129 L 434,123 L 444,122 L 456,116 L 473,100 L 490,98 L 494,94 L 503,101 L 511,95 L 515,95 L 517,100 L 524,101 L 526,99 L 533,99 L 539,106 L 544,107 L 550,113 L 546,118 L 547,120 L 551,117 L 568,113 L 582,98 L 585,103 L 584,108 L 587,112 L 605,119 L 610,123 L 613,137 L 619,144 L 627,142 L 633,142 L 634,144 L 635,140 L 637,140 L 637,154 L 658,190 L 671,238 L 683,258 L 685,265 L 691,267 L 690,270 L 679,276 L 660,276 L 658,274 L 649,273 L 647,269 L 644,270 L 619,256 L 610,256 L 600,260 L 593,257 L 585,257 L 581,260 L 578,259 L 560,264 L 557,262 L 552,268 L 543,270 L 507,264 L 502,259 L 507,254 L 498,237 L 469,206 L 453,197 L 426,193 L 397,184 L 394,178 L 388,175 L 393,137 L 406,121 L 421,109 L 422,93 L 420,88 L 423,87 L 424,89 L 433,90 L 436,87 L 444,85 L 445,82 L 449,82 Z"
    },
    "Morrowind": {
        "pinX": 835.0,
        "pinY": 360.0,
        "cap": "Mournhold",
        "path": "M 683,66 L 690,71 L 690,80 L 699,80 L 701,82 L 704,90 L 703,96 L 706,99 L 704,106 L 970,106 L 981,111 L 976,122 L 979,131 L 985,135 L 985,142 L 979,148 L 979,156 L 976,160 L 903,160 L 906,164 L 963,163 L 965,166 L 961,171 L 924,172 L 921,183 L 919,183 L 918,198 L 927,217 L 930,218 L 934,224 L 933,240 L 929,244 L 928,251 L 956,252 L 959,255 L 959,259 L 966,263 L 968,274 L 963,278 L 957,296 L 955,296 L 952,301 L 947,301 L 939,312 L 931,313 L 920,323 L 918,332 L 905,339 L 898,355 L 897,365 L 894,368 L 886,371 L 883,376 L 869,386 L 854,387 L 859,394 L 883,394 L 887,397 L 888,406 L 893,414 L 891,422 L 892,431 L 902,438 L 904,437 L 906,440 L 899,449 L 901,453 L 900,462 L 896,464 L 872,463 L 867,456 L 860,453 L 858,456 L 834,439 L 826,441 L 815,453 L 809,456 L 789,446 L 780,444 L 764,432 L 758,432 L 753,427 L 746,412 L 729,390 L 724,377 L 708,361 L 706,347 L 707,342 L 712,336 L 711,329 L 714,325 L 712,323 L 714,320 L 711,316 L 712,307 L 702,291 L 697,277 L 691,272 L 693,267 L 687,264 L 671,234 L 672,231 L 670,229 L 666,205 L 662,201 L 663,199 L 659,188 L 642,159 L 639,150 L 639,140 L 644,138 L 657,138 L 661,134 L 665,137 L 667,133 L 666,125 L 655,120 L 656,115 L 652,108 L 652,103 L 645,95 L 649,89 L 641,78 L 644,76 L 662,76 L 664,70 L 673,70 L 682,67 Z"
    },
    "Hammerfell": {
        "pinX": 210.0,
        "pinY": 275.0,
        "cap": "Sentinel",
        "path": "M 387,177 L 391,178 L 393,183 L 401,188 L 426,195 L 450,198 L 462,204 L 491,232 L 504,252 L 500,259 L 503,263 L 489,275 L 473,295 L 463,324 L 453,341 L 447,344 L 433,359 L 407,375 L 403,381 L 399,377 L 378,379 L 374,373 L 366,373 L 362,377 L 362,381 L 356,392 L 345,398 L 337,411 L 334,408 L 336,400 L 330,394 L 320,394 L 318,383 L 306,375 L 308,369 L 304,363 L 293,360 L 290,355 L 275,348 L 266,348 L 258,345 L 252,347 L 243,356 L 243,364 L 251,373 L 260,377 L 275,374 L 284,377 L 289,373 L 296,378 L 295,383 L 298,388 L 298,395 L 294,397 L 291,396 L 287,393 L 286,388 L 282,390 L 281,395 L 281,398 L 284,399 L 289,406 L 294,408 L 295,411 L 292,417 L 286,420 L 279,418 L 274,421 L 268,418 L 265,420 L 248,418 L 245,413 L 253,403 L 252,400 L 256,390 L 251,387 L 243,388 L 234,374 L 227,371 L 222,366 L 218,357 L 212,352 L 197,361 L 196,365 L 193,366 L 196,367 L 195,369 L 188,377 L 188,382 L 177,388 L 164,386 L 163,380 L 159,377 L 159,371 L 152,365 L 147,365 L 144,360 L 146,354 L 152,350 L 151,348 L 155,339 L 151,322 L 160,308 L 159,302 L 162,299 L 162,288 L 165,285 L 169,285 L 174,279 L 178,281 L 182,274 L 189,273 L 195,277 L 201,271 L 198,265 L 204,254 L 209,258 L 214,258 L 217,263 L 228,263 L 233,257 L 260,249 L 273,238 L 274,233 L 294,233 L 300,222 L 306,218 L 308,212 L 313,209 L 314,200 L 325,192 L 327,186 L 341,187 L 349,184 L 367,185 L 383,181 L 386,178 Z"
    },
    "Cyrodiil": {
        "pinX": 565.0,
        "pinY": 368.0,
        "cap": "Imperial City",
        "path": "M 612,257 L 614,259 L 618,257 L 646,271 L 648,274 L 660,278 L 679,278 L 689,272 L 696,277 L 701,291 L 711,307 L 710,316 L 713,320 L 711,322 L 713,325 L 710,329 L 711,336 L 706,342 L 705,347 L 706,359 L 723,377 L 734,400 L 743,409 L 752,427 L 757,432 L 738,450 L 728,484 L 717,507 L 695,529 L 677,551 L 673,561 L 671,576 L 664,590 L 654,596 L 650,596 L 649,589 L 641,586 L 638,580 L 640,572 L 639,566 L 638,568 L 633,568 L 633,575 L 628,583 L 618,587 L 621,577 L 616,543 L 616,529 L 622,507 L 621,493 L 612,482 L 593,467 L 541,456 L 522,457 L 513,463 L 513,460 L 498,446 L 487,442 L 477,442 L 459,444 L 442,450 L 434,449 L 419,456 L 411,464 L 399,471 L 372,475 L 370,470 L 374,463 L 371,460 L 353,458 L 349,447 L 344,444 L 343,440 L 344,429 L 349,424 L 348,417 L 355,411 L 358,405 L 375,394 L 401,388 L 407,377 L 434,360 L 447,346 L 450,346 L 454,342 L 465,324 L 470,305 L 476,293 L 493,273 L 504,264 L 517,268 L 522,267 L 526,270 L 533,269 L 543,272 L 551,270 L 557,264 L 560,266 L 577,261 L 580,262 L 586,258 L 588,260 L 593,259 L 597,261 L 611,258 Z"
    },
    "Summerset Isle": {
        "pinX": 150.0,
        "pinY": 615.0,
        "cap": "Alinor",
        "path": "M 209,494 L 246,495 L 267,507 L 271,510 L 272,516 L 280,520 L 281,541 L 283,546 L 289,548 L 292,553 L 292,608 L 289,613 L 288,624 L 287,626 L 271,628 L 237,629 L 237,675 L 232,681 L 228,691 L 221,692 L 219,696 L 187,696 L 181,693 L 177,688 L 109,688 L 100,685 L 95,679 L 94,674 L 90,672 L 87,664 L 87,604 L 79,595 L 81,588 L 86,585 L 98,585 L 99,580 L 108,571 L 109,555 L 123,527 L 143,527 L 154,517 L 201,517 L 202,498 L 208,495 Z"
    },
    "Valenwood": {
        "pinX": 420.0,
        "pinY": 530.0,
        "cap": "Falinesti",
        "path": "M 479,443 L 491,444 L 499,448 L 512,460 L 510,473 L 505,478 L 501,480 L 497,479 L 492,484 L 488,494 L 478,507 L 478,536 L 476,538 L 482,566 L 489,577 L 500,588 L 512,620 L 513,636 L 508,628 L 503,630 L 504,639 L 508,644 L 505,646 L 494,645 L 484,647 L 481,651 L 484,654 L 484,659 L 482,663 L 476,666 L 469,656 L 470,649 L 454,653 L 452,648 L 447,649 L 443,647 L 442,645 L 448,639 L 448,636 L 442,628 L 440,617 L 432,618 L 429,616 L 415,615 L 400,627 L 383,629 L 381,626 L 383,622 L 372,618 L 361,622 L 356,621 L 353,618 L 354,615 L 348,612 L 336,598 L 328,598 L 329,591 L 325,587 L 326,565 L 332,562 L 341,563 L 345,561 L 337,557 L 339,536 L 342,535 L 341,530 L 344,525 L 343,509 L 341,507 L 344,501 L 348,501 L 348,508 L 352,505 L 350,503 L 358,498 L 359,495 L 368,496 L 377,490 L 381,490 L 386,498 L 392,494 L 402,495 L 404,488 L 413,488 L 413,479 L 422,456 L 436,451 L 449,452 L 455,446 L 478,444 Z"
    },
    "Elsweyr": {
        "pinX": 550.0,
        "pinY": 600.0,
        "cap": "Torval",
        "path": "M 523,458 L 548,458 L 567,464 L 594,469 L 619,492 L 621,504 L 615,528 L 619,585 L 616,587 L 612,586 L 609,590 L 604,591 L 600,597 L 598,597 L 596,604 L 594,603 L 585,609 L 583,624 L 593,628 L 596,634 L 610,644 L 610,648 L 620,656 L 621,661 L 619,668 L 614,670 L 609,668 L 604,662 L 599,662 L 594,665 L 593,663 L 585,663 L 577,660 L 574,663 L 569,659 L 564,661 L 563,659 L 559,659 L 552,651 L 536,650 L 529,636 L 523,635 L 517,637 L 515,635 L 514,622 L 504,592 L 491,578 L 482,562 L 478,541 L 480,535 L 479,508 L 491,491 L 493,484 L 496,481 L 504,480 L 512,472 L 513,464 L 522,459 Z"
    },
    "Black Marsh": {
        "pinX": 770.0,
        "pinY": 520.0,
        "cap": "Stormhold",
        "path": "M 758,433 L 764,433 L 780,446 L 783,445 L 809,458 L 825,443 L 832,440 L 836,443 L 835,446 L 837,448 L 839,442 L 849,452 L 854,453 L 859,460 L 858,465 L 852,472 L 854,488 L 860,499 L 859,512 L 863,518 L 872,520 L 871,522 L 875,528 L 870,546 L 866,550 L 866,556 L 873,571 L 865,585 L 862,597 L 866,605 L 856,620 L 845,621 L 842,626 L 837,629 L 843,646 L 837,648 L 825,659 L 811,656 L 804,647 L 804,640 L 809,632 L 797,621 L 795,616 L 790,622 L 790,637 L 787,641 L 791,646 L 790,653 L 796,658 L 804,656 L 808,659 L 809,671 L 812,676 L 811,681 L 802,683 L 799,686 L 792,686 L 785,679 L 774,679 L 754,669 L 744,667 L 738,662 L 736,654 L 728,655 L 718,668 L 700,668 L 691,673 L 681,671 L 675,664 L 675,660 L 678,657 L 678,646 L 682,642 L 677,638 L 680,630 L 678,619 L 682,614 L 682,610 L 681,605 L 669,598 L 665,590 L 672,577 L 675,558 L 685,542 L 720,504 L 729,484 L 739,450 L 757,434 Z"
    }
};

async function openMapModal() {
    const modal = document.getElementById('map-modal');
    if (modal) modal.style.display = 'flex';
    await renderTamrielMap();
}

function closeMapModal() {
    const modal = document.getElementById('map-modal');
    if (modal) modal.style.display = 'none';
}

async function renderTamrielMap() {
    const container = document.getElementById('arena-map-container');
    const headerLoc = document.getElementById('map-location-header');
    if (!container) return;

    if (!cachedProvincesData) {
        try {
            const res = await fetch('/api/world/provinces');
            const data = await res.json();
            if (data.provinces) cachedProvincesData = data.provinces;
        } catch (e) {
            console.error("Error fetching provinces:", e);
        }
    }

    const world = (currentCharacterData && currentCharacterData.world) ? currentCharacterData.world : {};
    const curProvince = world.current_province || 'Cyrodiil';
    const curLocation = world.current_location || 'Imperial Dungeon';

    if (headerLoc) {
        headerLoc.innerHTML = `<strong>Current Position:</strong> ${curLocation}, <span style="color: var(--arena-gold);">${curProvince}</span>`;
    }

    if (!selectedProvinceName) selectedProvinceName = curProvince;

    const pinCoords = PROVINCE_MAP_COORDS[curProvince] || { pinX: 653.9, pinY: 416.8 };

    let clickZonesSvg = '';
    for (const [pName, data] of Object.entries(PROVINCE_MAP_COORDS)) {
        clickZonesSvg += `
            <g class="province-click-zone" style="cursor: pointer;" onmousemove="showMapProvinceTooltip(event, '${pName}')" onmouseleave="hideMapProvinceTooltip()" onclick="showMapProvinceTooltip(event, '${pName}')">
                <!-- Completely Invisible Province Click Hotspot -->
                <path d="${data.path}" fill="rgba(0,0,0,0.001)" stroke="transparent" stroke-width="1" fill-rule="evenodd" pointer-events="all" style="cursor: pointer;" />
            </g>
        `;
    }

    // High resolution Map SVG with floating cursor tooltip
    container.innerHTML = `
        <svg viewBox="0 0 1024 768" onmouseleave="hideMapProvinceTooltip()" style="width: 100%; height: auto; display: block; background: #000; border-radius: 8px; user-select: none;">
            <defs>
                <!-- Glowing Pin Filter -->
                <filter id="pinGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="3.5" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>

            <!-- Tamriel Map Image (1024x768) -->
            <image href="/static/img/tamriel_map.png" x="0" y="0" width="1024" height="768" />

            <!-- Invisible Click Hotspots for each province (no label badges) -->
            ${clickZonesSvg}

            <!-- Real-time Location Pin 📍 (Clean glowing concentric marker centered on Imperial City / active location) -->
            <g transform="translate(${pinCoords.pinX}, ${pinCoords.pinY})" filter="url(#pinGlow)" pointer-events="none">
                <!-- Pulse animation rings -->
                <circle cx="0" cy="0" r="18" fill="none" stroke-width="2.2" opacity="0.85" style="stroke: var(--gold-warm)">
                    <animate attributeName="r" values="8;30" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.9;0" dur="2s" repeatCount="indefinite" />
                </circle>
                <!-- Center Pin Marker -->
                <circle cx="0" cy="0" r="8" stroke-width="2" style="fill: var(--danger-vivid); stroke: #ffffff" />
                <circle cx="0" cy="0" r="3" fill="#ffffff" />
            </g>
        </svg>

        <!-- Floating Cursor Tooltip -->
        <div id="map-cursor-tooltip" style="position: absolute; top: 0; left: 0; pointer-events: none; z-index: 1000; background: hsla(var(--slate-h), var(--slate-s), 9%, 0.96); backdrop-filter: blur(12px); border: 1px solid hsla(var(--gold-h), var(--gold-s), 50%, 0.45); border-radius: 8px; padding: 10px 13px; max-width: 290px; box-shadow: 0 8px 24px rgba(0,0,0,0.85), 0 0 10px hsla(var(--gold-h), var(--gold-s), 50%, 0.2); opacity: 0; transform: scale(0.96); transition: opacity 0.12s ease, transform 0.12s ease;"></div>
    `;
}

let activeMapHoverProvince = null;

function showMapProvinceTooltip(e, pName) {
    const container = document.getElementById('arena-map-container');
    const tooltip = document.getElementById('map-cursor-tooltip');
    if (!container || !tooltip) return;

    activeMapHoverProvince = pName;
    const prov = (cachedProvincesData || []).find(p => p.name.toLowerCase() === pName.toLowerCase()) || {
        name: pName,
        dominant_race: "Inhabitants of Tamriel",
        climate: "Varied",
        culture_summary: "A storied realm within the Empire of Tamriel.",
        cities: []
    };

    const world = (currentCharacterData && currentCharacterData.world) ? currentCharacterData.world : {};
    const isCurrent = (world.current_province || '').toLowerCase() === pName.toLowerCase();

    tooltip.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px;">
            <h4 style="margin: 0; font-size: 0.94rem; color: var(--gold-bright); font-family: var(--font-heading); text-transform: uppercase; letter-spacing: 0.8px;">
                ${prov.name}
            </h4>
            ${isCurrent ? '<span style="font-size: 0.58rem; padding: 1px 6px; border-radius: 3px; background: hsla(var(--green-h), 70%, 45%, 0.2); color: var(--success-bright); border: 1px solid hsla(var(--green-h), 70%, 45%, 0.4); font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;">Current</span>' : ''}
        </div>
        <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 4px;">
            <strong>Climate:</strong> ${prov.climate || 'Temperate'} • <strong>Heritage:</strong> ${prov.dominant_race || 'Native'}
        </div>
        <p style="margin: 0 0 6px 0; font-size: 0.75rem; color: var(--text-main); line-height: 1.35;">
            ${prov.culture_summary || ''}
        </p>
        <div style="font-size: 0.70rem; color: var(--text-dim);">
            <strong style="color: var(--text-muted);">Cities:</strong> ${(prov.cities || []).join(', ') || 'Settlements'}
        </div>
    `;

    positionMapProvinceTooltip(e);
    tooltip.style.opacity = '1';
    tooltip.style.transform = 'scale(1)';
}

function positionMapProvinceTooltip(e) {
    const container = document.getElementById('arena-map-container');
    const tooltip = document.getElementById('map-cursor-tooltip');
    if (!container || !tooltip || !activeMapHoverProvince) return;

    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const tooltipWidth = tooltip.offsetWidth || 280;
    const tooltipHeight = tooltip.offsetHeight || 140;

    let left = mouseX + 14;
    let top = mouseY + 14;

    // Flip horizontally if close to right edge
    if (left + tooltipWidth > rect.width - 10) {
        left = mouseX - tooltipWidth - 14;
    }
    // Flip vertically if close to bottom edge
    if (top + tooltipHeight > rect.height - 10) {
        top = mouseY - tooltipHeight - 14;
    }

    // Clamp strictly within map container borders
    left = Math.max(8, Math.min(rect.width - tooltipWidth - 8, left));
    top = Math.max(8, Math.min(rect.height - tooltipHeight - 8, top));

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
}

function hideMapProvinceTooltip() {
    activeMapHoverProvince = null;
    const tooltip = document.getElementById('map-cursor-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
        tooltip.style.transform = 'scale(0.96)';
    }
}

function showDebugToast(message) {
    let container = document.getElementById('debug-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'debug-toast-container';
        container.style.cssText = 'position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 10000; width: 90%; max-width: 500px; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.style.cssText = 'background: hsla(0, 85%, 60%, 0.95); color: white; padding: 12px 16px; border-radius: 8px; font-family: monospace; font-size: 0.8rem; box-shadow: 0 4px 12px rgba(0,0,0,0.5); pointer-events: auto; word-break: break-all; border-left: 4px solid var(--danger-bright);';
    toast.innerHTML = `<div style="font-weight: bold; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; stroke: var(--danger-bright);"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>Application Error</div><div>${message}</div><button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; text-decoration: underline; margin-top: 8px; cursor: pointer; padding: 0; font-size: 0.75rem;">Dismiss</button>`;
    container.appendChild(toast);
}

/* ==========================================================================
   I. CONFIGURATION, GLOBAL STATE CONSTANTS & CACHING
   ========================================================================== */

/* ==========================================================================
   I. CONFIGURATION, GLOBAL STATE CONSTANTS & CACHING
   ========================================================================== */

const safeLocalStorage = {
    getItem(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    },
    setItem(key, value) {
        try { localStorage.setItem(key, value); } catch (e) {}
    },
    removeItem(key) {
        try { localStorage.removeItem(key); } catch (e) {}
    }
};

const safeSessionStorage = {
    getItem(key) {
        try { return sessionStorage.getItem(key); } catch (e) { return null; }
    },
    setItem(key, value) {
        try { sessionStorage.setItem(key, value); } catch (e) {}
    },
    removeItem(key) {
        try { sessionStorage.removeItem(key); } catch (e) {}
    }
};

const appConfig = window.__ARENA_CONFIG || {};
const localIp = appConfig.localIp || "127.0.0.1";
let chatContainer = document.getElementById('chat-container');
let userInput = document.getElementById('user-input');
let programWelcomeMessage = null;
let activePlayerName = (appConfig && appConfig.userName) || "";

function replacePlaceholders(text) {
    if (!text) return text;
    const displayUser = getUserDisplayName();
    const displayChar = activeProgramName || "Program";
    return text.replace(new RegExp("{" + "{" + "user" + "}" + "}", "gi"), displayUser)
               .replace(new RegExp("{" + "{" + "char" + "}" + "}", "gi"), displayChar);
}

let isAtBottom = true;
if (chatContainer) {
    // Setup modern lag-free bottom sentinel using IntersectionObserver
    const bottomSentinel = document.createElement('div');
    bottomSentinel.id = 'bottom-sentinel';
    bottomSentinel.style.cssText = 'height: 1px; width: 100%; flex-shrink: 0; margin-top: -20px; pointer-events: none;';
    chatContainer.appendChild(bottomSentinel);

    const scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            isAtBottom = entry.isIntersecting;
        });
    }, {
        root: chatContainer,
        threshold: 0.1
    });
    scrollObserver.observe(bottomSentinel);

    // Automatically keep bottom-sentinel as the last child
    const mutationObserver = new MutationObserver(() => {
        if (chatContainer.lastChild !== bottomSentinel) {
            mutationObserver.disconnect();
            chatContainer.appendChild(bottomSentinel);
            mutationObserver.observe(chatContainer, { childList: true });
        }
    });
    mutationObserver.observe(chatContainer, { childList: true });

    // Keep scroll at bottom when images load, if user was at the bottom
    chatContainer.addEventListener('load', (e) => {
        if (e.target.tagName.toLowerCase() === 'img') {
            if (isAtBottom) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
    }, { capture: true, passive: true }); // Capture phase, passive scroll-safe listener
}

let skipScrollSave = false;

function saveChatScrollState() {
    if (skipScrollSave) return;
    if (chatContainer) {
        safeSessionStorage.setItem('chat_scroll_pos', chatContainer.scrollTop);
        const isAtBottom = (chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 50);
        safeSessionStorage.setItem('chat_was_at_bottom', isAtBottom);
    }
}

window.addEventListener('beforeunload', saveChatScrollState);
window.addEventListener('pagehide', saveChatScrollState);

function reloadApp(skipSave = false, forceHardReload = false) {
    if (skipSave) {
        skipScrollSave = true;
        safeSessionStorage.removeItem('chat_scroll_pos');
        safeSessionStorage.removeItem('chat_was_at_bottom');
    }
    if (forceHardReload) {
        location.reload();
    } else {
        softReloadApp();
    }
}



async function softReloadApp() {
    try {
        const [historyRes, _] = await Promise.all([
            fetch(`/history?session_id=${sessionId}&t=${Date.now()}`),
            loadServerImages()
        ]);
        const data = await historyRes.json();
        
        if (data.welcome_message) {
            programWelcomeMessage = data.welcome_message;
        } else {
            programWelcomeMessage = null;
        }
        
        if (data.active_program) {
            applyTheme(data.active_program, data.theme);
        }
        if (data.character_name) {
            activeProgramName = data.character_name;
            const programTitle = "LM Arena";
            document.title = programTitle;
            
            const headerTitle = document.querySelector('.header-title-area h1');
            if (headerTitle) {
                headerTitle.textContent = programTitle;
            }
            
            const userInput = document.getElementById('user-input');
            if (userInput) {
                userInput.placeholder = "What do you do?";
            }
        }
        
        // Refresh avatar profile buster and select model options
        profileCacheBuster = Date.now();
        updateProfileImages();
        modelInitPromise = initializeModelSelect();

        const newHistory = (data.history || []).filter(msg => {
            if (msg.id && msg.id.startsWith('sys_')) return false;
            return true;
        });
        
        // Temporarily disable smooth scroll while updating/diffing the DOM
        chatContainer.classList.remove('smooth-scroll');

        // Snapshot scroll position before DOM mutations to keep the viewport anchored
        const savedScrollTop = chatContainer.scrollTop;

        let domUpdated = false;
        
        // Pre-remove any message rows from the DOM that are no longer in the server history.
        // This keeps indices perfectly aligned and prevents shifting issues during updates.
        const newHistoryIds = new Set(newHistory.map(msg => msg.id).filter(Boolean));
        const currentLiveRows = Array.from(chatContainer.querySelectorAll('.message-row:not(#welcome-message):not(#onboarding-container)'));
        currentLiveRows.forEach(row => {
            const rowId = row.dataset.msgId;
            const isTransient = row.querySelector('[data-is-transient="true"]') || row.dataset.isTransient === "true";
            if (rowId && !newHistoryIds.has(rowId) && !isTransient) {
                row.remove();
                domUpdated = true;
            }
        });
        
        newHistory.forEach((msg, idx) => {
            const msgId = msg.id;
            const hash = computeContentHash(msg);
            
            // Find if a row with this msgId already exists in the DOM
            let existingRow = null;
            if (msgId) {
                existingRow = chatContainer.querySelector(`.message-row[data-msg-id="${msgId}"]`);
            }
            
            if (existingRow) {
                if (existingRow.dataset.contentHash !== hash) {
                    // Elements changed, replace in-place
                    const newRow = renderMessage(msg);
                    chatContainer.replaceChild(newRow, existingRow);
                    existingRow = newRow;
                    domUpdated = true;
                }
            } else {
                // Element is new, create it
                existingRow = renderMessage(msg);
                domUpdated = true;
            }
            
            if (existingRow) {
                // Ensure existingRow is at the correct position (relative to message-rows)
                const liveRows = Array.from(chatContainer.querySelectorAll('.message-row:not(#welcome-message):not(#onboarding-container)'));
                const currentChildAtIdx = liveRows[idx];
                if (currentChildAtIdx !== existingRow) {
                    if (currentChildAtIdx) {
                        chatContainer.insertBefore(existingRow, currentChildAtIdx);
                    } else {
                        const sentinel = document.getElementById('bottom-sentinel');
                        if (sentinel) {
                            chatContainer.insertBefore(existingRow, sentinel);
                        } else {
                            chatContainer.appendChild(existingRow);
                        }
                    }
                    domUpdated = true;
                }
            }
        });
        
        // Clean onboarding or welcome if we now have messages
        if (newHistory.length > 0) {
            const welcome = document.getElementById('welcome-message');
            if (welcome) welcome.remove();
            const onboarding = document.getElementById('onboarding-container');
            if (onboarding) onboarding.remove();
        } else {
            if (!connectionStatus.remote_configured  && !connectionStatus.local_online) {
                showOnboardingCard();
            } else {
                showWelcomeMessage();
            }
        }
        
        fetchCharacterStatus();
        
        // Maintain scroll posture
        if (domUpdated) {
            if (isAtBottom) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                chatContainer.scrollTop = savedScrollTop;
            }
        }
    } catch (error) {
        console.error("Error soft-reloading chat history:", error);
    } finally {
        // Re-enable smooth scroll
        setTimeout(() => {
            chatContainer.classList.add('smooth-scroll');
        }, 50);
    }
}

// Restore drafted/unsent message if preserved in sessionStorage
if (userInput) {
    const stagedMessage = sessionStorage.getItem('staged_message');
    if (stagedMessage) {
        userInput.value = stagedMessage;
        // Auto-resize once browser is ready
        setTimeout(() => {
            userInput.style.height = 'auto';
            userInput.style.height = (userInput.scrollHeight) + 'px';
        }, 100);
    }
}

// TTS Configuration and State
let ttsAutoSpeak = appConfig.ttsAutoSpeak || false;
const ttsProvider = appConfig.ttsProvider || "local";
let currentAudio = null;
let currentPlayingBtn = null;

let currentHeartState = {
    name: "calm",
    color: "#85b9eb",
    glow: "rgba(133, 185, 235, 0.9)",
    speed: "2.0s",
    intensity: 0.0
};

function initHeartPulse() {
    const heartElement = document.querySelector('.heart-pulse');
    if (heartElement) {
        heartElement.style.cursor = 'pointer';
        heartElement.addEventListener('click', (e) => {
            e.stopPropagation();
            openStatusModal();
        });
    }
    fetchCharacterStatus();
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeartPulse);
} else {
    initHeartPulse();
}

// Unregister Service Workers to prevent aggressive caching of templates/static assets
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
        for (let registration of registrations) {
            registration.unregister()
                .then(success => {
                    if (success) {
                        console.log('Service Worker unregistered successfully');
                    }
                });
        }
    });
}

// Update heart icon to reflect Program's current emotional state

/* ==========================================================================
   II. 1. UTILITY HELPERS & COMMON MIDDLEWARE
   ========================================================================== */

// --- getRelativePath ---

/* ==========================================================================
   II. 1. UTILITY HELPERS & COMMON MIDDLEWARE
   ========================================================================== */

// --- getRelativePath ---
function getRelativePath(url) {
    if (!url) return '';
    try {
        const parsed = new URL(url, window.location.origin);
        return parsed.pathname;
    } catch (e) {
        return url;
    }
}

// --- generateMessageId ---
function generateMessageId(text, role = 'user') {
    let prefix = 'msg_';
    if (role === 'program' || role === 'user') {
        if (text && text.trim().startsWith('![') && text.trim().endsWith(')')) {
            prefix = 'img_';
        } else if (role === 'program') {
            if (text && (text.includes('Error') || text.includes('failed') || text.includes('momentarily overwhelmed'))) {
                prefix = 'err_';
            } else {
                prefix = 'prgm_';
            }
        } else {
            if (text && (text.includes("Send me a portrait of yourself") || text.includes("[GENERATE_IMAGE:") || text.includes("[GENERATE_IMAGEN:"))) {
                prefix = 'port_';
            } else if (text && text.startsWith("[SYSTEM: User has completed")) {
                prefix = 'quest_';
            } else if (text && text.startsWith("[Tool Response from")) {
                prefix = 'tool_';
            } else {
                prefix = 'usr_';
            }
        }
    } else if (role === 'voice-call') {
        prefix = 'vc_';
    } else if (role === 'system-memory' || role === 'system') {
        prefix = 'sys_';
    }
    let hash = 0;
    const str = text || '';
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return prefix + Math.abs(hash).toString(36) + '_' + str.length;
}

// --- escapeHtml ---
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- setupCustomDropdown ---
function setupCustomDropdown(select) {
    if (!select) return;
    if (select.dataset.customDropdownSetup) return;
    select.dataset.customDropdownSetup = "true";

    // Hide native select
    select.style.display = "none";

    // Create container
    const container = document.createElement("div");
    container.className = "custom-dropdown-container";
    if (select.id) {
        container.id = select.id + "-custom-container";
    }

    // Create trigger
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "custom-dropdown-trigger";
    
    const triggerText = document.createElement("span");
    triggerText.className = "custom-dropdown-trigger-text";
    trigger.appendChild(triggerText);
    
    container.appendChild(trigger);

    // Create list
    const list = document.createElement("div");
    list.className = "custom-dropdown-list";
    container.appendChild(list);

    // Insert container after select
    select.parentNode.insertBefore(container, select.nextSibling);

    // Function to rebuild options
    function rebuild() {
        list.innerHTML = "";
        const options = Array.from(select.options);
        
        if (options.length === 0) {
            triggerText.textContent = select.disabled ? "Loading..." : "No options";
            return;
        }

        // Update trigger text with active option
        const activeOption = select.options[select.selectedIndex] || select.options[0];
        triggerText.textContent = activeOption ? activeOption.textContent : "";
        
        options.forEach((opt, idx) => {
            const item = document.createElement("div");
            item.className = "custom-dropdown-item";
            item.textContent = opt.textContent;
            item.dataset.value = opt.value;
            item.dataset.index = idx;
            
            if (idx === select.selectedIndex) {
                item.classList.add("selected");
            }
            
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                select.selectedIndex = idx;
                
                // Trigger change event on native select
                const event = new Event("change", { bubbles: true });
                select.dispatchEvent(event);
                
                // Close list
                container.classList.remove("open");
                list.style.display = "none";
            });
            
            list.appendChild(item);
        });
        
        // Keep trigger disabled state in sync
        trigger.disabled = select.disabled;
        if (select.disabled) {
            container.classList.add("disabled");
        } else {
            container.classList.remove("disabled");
        }
    }

    // Click trigger to toggle
    trigger.addEventListener("click", (e) => {
        e.stopPropagation();
        if (select.disabled) return;
        
        // Close all other custom dropdowns first
        document.querySelectorAll(".custom-dropdown-container").forEach(c => {
            if (c !== container) {
                c.classList.remove("open");
                const l = c.querySelector(".custom-dropdown-list");
                if (l) l.style.display = "none";
            }
        });

        const isOpen = container.classList.toggle("open");
        list.style.display = isOpen ? "block" : "none";
    });

    // Document click to close
    document.addEventListener("click", () => {
        container.classList.remove("open");
        list.style.display = "none";
    });

    // Initial build
    rebuild();

    // Observe native select for option changes
    const observer = new MutationObserver(() => {
        rebuild();
    });
    observer.observe(select, { childList: true, subtree: true });

    // Watch for value changes via property setter
    const origDescriptorVal = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
    const origDescriptorIdx = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "selectedIndex");
    
    if (origDescriptorVal && origDescriptorVal.set) {
        Object.defineProperty(select, "value", {
            get() {
                return origDescriptorVal.get.call(select);
            },
            set(val) {
                origDescriptorVal.set.call(select, val);
                rebuild();
            }
        });
    }
    
    if (origDescriptorIdx && origDescriptorIdx.set) {
        Object.defineProperty(select, "selectedIndex", {
            get() {
                return origDescriptorIdx.get.call(select);
            },
            set(idx) {
                origDescriptorIdx.set.call(select, idx);
                rebuild();
            }
        });
    }

    // Watch for disabled state changes
    const attrObserver = new MutationObserver((mutations) => {
        mutations.forEach(m => {
            if (m.attributeName === "disabled") {
                trigger.disabled = select.disabled;
                if (select.disabled) {
                    container.classList.add("disabled");
                } else {
                    container.classList.remove("disabled");
                }
            }
        });
    });
    attrObserver.observe(select, { attributes: true, attributeFilter: ["disabled"] });
}

/* ==========================================================================
   III. 2. ONBOARDING & GLOBAL CONFIG CONTROLLERS
   ========================================================================== */

// --- initializeModelSelect ---
async function initializeModelSelect() {
    try {
        const response = await fetch('/models');
        const data = await response.json();
        const modelSelectElement = document.getElementById('model-select');
        if (!modelSelectElement) return;

        // Update connection status variables
        if (data.status) {
            connectionStatus = data.status;
            updateConnectionModalStatus();
            if (document.getElementById('onboarding-container')) {
                showOnboardingCard();
            }
        }

        // Check if the models list has actually changed
        const currentModelsJSON = JSON.stringify(data.models || []);
        const lastModelsJSON = modelSelectElement.dataset.lastModelsJson || "";
        if (currentModelsJSON !== lastModelsJSON) {
            modelSelectElement.dataset.lastModelsJson = currentModelsJSON;
            modelSelectElement.innerHTML = '';
            availableModels = data.models || [];
            
            // If no models are available, add a disconnected/paused local placeholder
            if (availableModels.length === 0) {
                const opt = document.createElement('option');
                opt.value = 'local-llm';
                if (data.status && data.status.local_online) {
                    opt.textContent = 'Local Model (No Model Loaded)';
                } else {
                    opt.textContent = 'Local Model (Disconnected)';
                }
                modelSelectElement.appendChild(opt);
            } else {
                availableModels.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model.value;
                    opt.textContent = model.label;
                    modelSelectElement.appendChild(opt);
                });
            }

            const defaultModel = data.default || 'local-llm';
            safeLocalStorage.setItem('program_default_model', defaultModel);

            let storedModel = safeLocalStorage.getItem('program_selected_model');
            const isValid = availableModels.some(m => m.value === storedModel) || (storedModel === 'local-llm' && availableModels.length === 0);
            if (!isValid) {
                storedModel = defaultModel;
                safeLocalStorage.setItem('program_selected_model', storedModel);
            }
            
            selectedModel = storedModel;
            modelSelectElement.value = selectedModel;
        }
        modelSelectElement.disabled = false;
    } catch (error) {
        console.error("Error fetching model configuration:", error);
        const modelSelectElement = document.getElementById('model-select');
        if (modelSelectElement) {
            modelSelectElement.disabled = false;
            if (modelSelectElement.children.length === 0) {
                const opt = document.createElement('option');
                opt.value = 'local-llm';
                opt.textContent = 'Local Model (Disconnected)';
                modelSelectElement.appendChild(opt);
            }
        }
    }
}

// --- showOnboardingCard ---
function showOnboardingCard() {
    // Remove existing welcome or onboarding first
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();
    let onboarding = document.getElementById('onboarding-container');
    if (onboarding) onboarding.remove();
    
    onboarding = document.createElement('div');
    onboarding.id = 'onboarding-container';
    onboarding.className = 'onboarding-card';

    // Build local LLM onboarding card section based on engine state
    let localContent = '';
    if (connectionStatus.local_online === 'starting' || _localStarting) {
        localContent = `
            <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">Local LLM engine is starting up in the background. Please wait...</p>
            <button disabled class="onboarding-btn connect-cloud-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-bottom: 15px; opacity: 0.7;">Starting...</button>
        `;
    } else if (_localStopping) {
        localContent = `
            <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">Local LLM engine is stopping. Please wait...</p>
            <button disabled class="onboarding-btn connect-cloud-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-bottom: 15px; opacity: 0.7;">Stopping...</button>
        `;
    } else if (!connectionStatus.local_online) {
        localContent = `
            <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">Local LLM engine is offline. Start the server or search Hugging Face below to download a GGUF model.</p>
            <button onclick="startLocalLLM(this)" class="onboarding-btn connect-cloud-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-bottom: 15px;">Start Server</button>
            
            <div style="border-top: 1px solid var(--border-color); padding-top: 15px;">
                <label style="font-size: 0.72rem; color: var(--text-muted); font-weight: 500;">Search Hugging Face (GGUF)</label>
                <div style="display: flex; gap: 8px; margin-top: 5px;">
                    <input type="text" id="hf-search-input" placeholder="e.g. qwen2.5-0.5b" class="onboarding-input" style="flex: 1; font-size: 0.8rem; padding: 6px;" onkeydown="if(event.key==='Enter') searchHFModels('hf-search-input', 'hf-search-results')">
                    <button onclick="searchHFModels('hf-search-input', 'hf-search-results')" class="onboarding-btn" style="margin: 0; padding: 0 15px; font-size: 0.8rem;">Search</button>
                </div>
                <div id="hf-search-results" style="margin-top: 10px; max-height: 150px; overflow-y: auto; font-size: 0.8rem; display: flex; flex-direction: column; gap: 6px;"></div>
            </div>
        `;
    } else {
        localContent = `
            <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">Local LLM engine is running and active.</p>
            <div class="local-steps" style="font-size: 0.8rem; gap: 6px; margin-bottom: 15px;">
                <div class="step-item" style="color: var(--success-bright);">
                    <span class="step-num" style="background: hsla(115, 70%, 45%, 0.12); color: var(--success-bright); border: 1px solid hsla(115, 70%, 45%, 0.25);">✓</span>
                    <span>Engine online. Choose a model in the header selector to start conversing.</span>
                </div>
            </div>

            
            <div style="border-top: 1px solid var(--border-color); padding-top: 15px;">
                <label style="font-size: 0.72rem; color: var(--text-muted); font-weight: 500;">Search Hugging Face (GGUF)</label>
                <div style="display: flex; gap: 8px; margin-top: 5px;">
                    <input type="text" id="hf-search-input" placeholder="e.g. qwen2.5-0.5b" class="onboarding-input" style="flex: 1; font-size: 0.8rem; padding: 6px;" onkeydown="if(event.key==='Enter') searchHFModels('hf-search-input', 'hf-search-results')">
                    <button onclick="searchHFModels('hf-search-input', 'hf-search-results')" class="onboarding-btn" style="margin: 0; padding: 0 15px; font-size: 0.8rem;">Search</button>
                </div>
                <div id="hf-search-results" style="margin-top: 10px; max-height: 150px; overflow-y: auto; font-size: 0.8rem; display: flex; flex-direction: column; gap: 6px;"></div>
            </div>
        `;
    }
    
    onboarding.innerHTML = `
        <div class="onboarding-header">
            <h2>👾 LM-Arena Connection Guide</h2>
            <p>Your program needs a language model "brain" to speak. Choose one or both options below to connect.</p>
        </div>
        
        <div class="onboarding-options">
            <!-- Option 1: Cloud Gemini -->
            <div class="onboarding-option-box cloud-box">
                <div class="option-header">
                    <h3>Remote Connection (Cloud)</h3>
                    <span id="onboarding-gemini-status" class="status-badge ${connectionStatus.remote_configured ? 'status-configured' : 'status-unconfigured'}">
                        ${connectionStatus.remote_configured ? 'Configured' : 'Unconfigured'}
                    </span>
                </div>
                <p class="option-desc">Connect to a remote cloud LLM. Requires an API Key and Server URL.</p>
                <div class="input-group">
                    <label for="onboarding-api-key">Remote API Key</label>
                    <input type="password" id="onboarding-api-key" placeholder="e.g. sk-or-... or AIzaSy..." class="onboarding-input">
                </div>
                <div class="input-group">
                    <label for="onboarding-project-id">Remote Server URL</label>
                    <input type="text" id="onboarding-project-id" placeholder="https://api.deepseek.com/v1/chat/completions" class="onboarding-input">
                </div>
                <div class="input-group">
                    <label for="onboarding-gemini-model">Remote Model Name</label>
                    <input type="text" id="onboarding-gemini-model" placeholder="e.g. deepseek-chat or gpt-4o" class="onboarding-input">
                </div>
                <button onclick="saveOnboardingConfig()" class="onboarding-btn connect-cloud-btn">Save & Connect Cloud</button>
                <div class="helper-text">
                    Save credentials to enable remote model offloading.
                </div>
            </div>

            <!-- Option 2: Local LLM -->
            <div class="onboarding-option-box local-box">
                <div class="option-header">
                    <h3>Local LLM</h3>
                    <span id="onboarding-local-status" class="status-badge ${connectionStatus.local_online === 'starting' ? 'status-starting' : (connectionStatus.local_online ? 'status-online' : 'status-offline')}">
                        ${connectionStatus.local_online === 'starting' ? 'Starting...' : (connectionStatus.local_online ? 'Online' : 'Offline')}
                    </span>
                </div>
                ${localContent}
            </div>
        </div>
        
        <div class="onboarding-footer">
            <span>Active Configuration File:</span>
            <code class="env-path">C:/LLM/LM-Arena/.env</code>
        </div>
    `;
    chatContainer.appendChild(onboarding);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// --- saveConfigData ---
async function saveConfigData(apiKey, projectId, geminiModel = null) {
    if (!apiKey && !projectId && !geminiModel) {
        showCustomAlert("Validation Error", "Please provide at least one configuration value.");
        return;
    }
    try {
        const bodyObj = {};
        if (apiKey) bodyObj.remote_api_key = apiKey;
        if (projectId) bodyObj.remote_cloud_url = projectId;
        if (geminiModel) bodyObj.remote_model = geminiModel;

        const res = await fetch('/api/save_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyObj)
        });
        const data = await res.json();
        if (data.error) {
            showCustomAlert("Error Saving Config", data.error);
        } else {
            showCustomAlert("Configuration Saved", "Your credentials have been successfully updated.");
            await initializeModelSelect();
            if (connectionStatus.remote_configured  || connectionStatus.local_online) {
                const onboarding = document.getElementById('onboarding-container');
                if (onboarding) onboarding.remove();
                showWelcomeMessage();
            }
            closeConnectionModal();
        }
    } catch (e) {
        console.error("Error saving config:", e);
        showCustomAlert("Error", "Failed to contact server to save config.");
    }
}

// --- saveOnboardingConfig ---
function saveOnboardingConfig() {
    const apiKey = document.getElementById('onboarding-api-key').value;
    const projectId = document.getElementById('onboarding-project-id').value;
    const geminiModel = document.getElementById('onboarding-gemini-model').value;
    saveConfigData(apiKey, projectId, geminiModel);
}

// --- saveModalConfig ---
function saveModalConfig() {
    const apiKey = document.getElementById('modal-api-key').value;
    const projectId = document.getElementById('modal-project-id').value;
    const geminiModel = document.getElementById('modal-gemini-model').value;
    saveConfigData(apiKey, projectId, geminiModel);
}

// --- Ambient BGM & Speech Audio Manager ---
let audioTrackPlayer = null;
let currentTrackPath = null;
let audioVolume = 0.6; // 0.0 to 1.0
let isAudioMuted = false;
let speechVolume = 1.0; // 0.0 to 1.0
let isSpeechMuted = false;
let useImagenMode = false;

function initAudioSystem() {
    const savedVol = safeLocalStorage.getItem('arena_audio_volume');
    if (savedVol !== null) {
        audioVolume = parseFloat(savedVol);
    }
    const savedMute = safeLocalStorage.getItem('arena_audio_muted');
    if (savedMute === 'true') {
        isAudioMuted = true;
    }
    const savedSpeechVol = safeLocalStorage.getItem('arena_speech_volume');
    if (savedSpeechVol !== null) {
        speechVolume = parseFloat(savedSpeechVol);
    }
    const savedSpeechMute = safeLocalStorage.getItem('arena_speech_muted');
    if (savedSpeechMute === 'true') {
        isSpeechMuted = true;
    }
    const savedImagen = safeLocalStorage.getItem('arena_use_imagen');
    if (savedImagen === 'true') {
        useImagenMode = true;
    }

    const slider = document.getElementById('audio-volume-slider');
    const display = document.getElementById('audio-volume-display');
    if (slider) slider.value = Math.round(audioVolume * 100);
    if (display) display.textContent = `${Math.round(audioVolume * 100)}%`;

    const speechSlider = document.getElementById('speech-volume-slider');
    const speechDisplay = document.getElementById('speech-volume-display');
    if (speechSlider) speechSlider.value = Math.round(speechVolume * 100);
    if (speechDisplay) speechDisplay.textContent = `${Math.round(speechVolume * 100)}%`;

    updateMuteButtonUI();
    updateSpeechMuteButtonUI();
    updateImagenToggleUI();

    // Immediate startup track request based on world state
    if (currentCharacterData && currentCharacterData.world) {
        updateMusicFromWorldState();
    } else {
        playBGMTrack("Opening Titles.mp3");
    }

    // Unified document unlocker for browser policies
    const unlockEvents = ['pointerdown', 'mousedown', 'keydown', 'touchstart', 'scroll'];
    const unlocker = () => {
        if (audioTrackPlayer && audioTrackPlayer.paused) {
            audioTrackPlayer.play().catch(() => {});
        } else if (!audioTrackPlayer) {
            if (currentCharacterData && currentCharacterData.world) {
                updateMusicFromWorldState();
            } else {
                playBGMTrack("Opening Titles.mp3");
            }
        }
        unlockEvents.forEach(evt => {
            window.removeEventListener(evt, unlocker);
        });
    };
    unlockEvents.forEach(evt => {
        window.addEventListener(evt, unlocker, { passive: true });
    });
}

function toggleImagenMode() {
    useImagenMode = !useImagenMode;
    safeLocalStorage.setItem('arena_use_imagen', useImagenMode.toString());
    updateImagenToggleUI();
}

function updateImagenToggleUI() {
    const checkbox = document.getElementById('imagen-toggle-checkbox');
    if (checkbox) {
        checkbox.checked = useImagenMode;
    }
}

function onAudioVolumeInput(val) {
    audioVolume = parseFloat(val) / 100;
    safeLocalStorage.setItem('arena_audio_volume', audioVolume.toString());
    const display = document.getElementById('audio-volume-display');
    if (display) display.textContent = `${Math.round(audioVolume * 100)}%`;

    if (audioTrackPlayer) {
        audioTrackPlayer.volume = isAudioMuted ? 0 : audioVolume;
    }
}

function toggleAudioMute() {
    isAudioMuted = !isAudioMuted;
    safeLocalStorage.setItem('arena_audio_muted', isAudioMuted.toString());
    updateMuteButtonUI();

    if (audioTrackPlayer) {
        audioTrackPlayer.volume = isAudioMuted ? 0 : audioVolume;
    }
}

function updateMuteButtonUI() {
    const icon = document.getElementById('audio-mute-icon');
    if (!icon) return;
    if (isAudioMuted) {
        icon.innerHTML = `
            <line x1="1" y1="1" x2="23" y2="23"></line>
            <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
            <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
        `;
    } else {
        icon.innerHTML = `
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        `;
    }
}

function onSpeechVolumeInput(val) {
    speechVolume = parseFloat(val) / 100;
    safeLocalStorage.setItem('arena_speech_volume', speechVolume.toString());
    const display = document.getElementById('speech-volume-display');
    if (display) display.textContent = `${Math.round(speechVolume * 100)}%`;

    if (typeof currentAudio !== 'undefined' && currentAudio) {
        currentAudio.volume = isSpeechMuted ? 0 : speechVolume;
    }
    if (typeof voiceCallActiveAudio !== 'undefined' && voiceCallActiveAudio) {
        voiceCallActiveAudio.volume = isSpeechMuted ? 0 : speechVolume;
    }
}

function toggleSpeechMute() {
    isSpeechMuted = !isSpeechMuted;
    safeLocalStorage.setItem('arena_speech_muted', isSpeechMuted.toString());
    updateSpeechMuteButtonUI();

    if (typeof currentAudio !== 'undefined' && currentAudio) {
        currentAudio.volume = isSpeechMuted ? 0 : speechVolume;
    }
    if (typeof voiceCallActiveAudio !== 'undefined' && voiceCallActiveAudio) {
        voiceCallActiveAudio.volume = isSpeechMuted ? 0 : speechVolume;
    }
}

function updateSpeechMuteButtonUI() {
    const icon = document.getElementById('speech-mute-icon');
    if (!icon) return;
    if (isSpeechMuted) {
        icon.innerHTML = `
            <line x1="1" y1="1" x2="23" y2="23"></line>
            <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
            <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
        `;
    } else {
        icon.innerHTML = `
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        `;
    }
}

function playBGMTrack(trackFilename, isLooping = true) {
    if (!trackFilename) return;
    const trackPath = `/sound/${encodeURIComponent(trackFilename)}`;
    if (currentTrackPath === trackPath && audioTrackPlayer && !audioTrackPlayer.paused) {
        return;
    }

    if (!audioTrackPlayer) {
        audioTrackPlayer = new Audio();
    }

    audioTrackPlayer.src = trackPath;
    audioTrackPlayer.loop = isLooping;
    audioTrackPlayer.volume = isAudioMuted ? 0 : audioVolume;
    currentTrackPath = trackPath;

    audioTrackPlayer.play().catch(e => {
        console.log("Audio autoplay waiting for user interaction:", e);
    });
}

function updateMusicFromWorldState(world, vitals) {
    world = world || (window.currentCharacterData ? window.currentCharacterData.world : null) || {};
    vitals = vitals || (window.currentCharacterData && window.currentCharacterData.character ? (window.currentCharacterData.character.vitals || window.currentCharacterData.character.derived) : null) || {};

    const charHP = (vitals.hp_current !== undefined) ? vitals.hp_current : (vitals.hp !== undefined ? vitals.hp : null);
    const isDead = vitals.dead === true || (charHP !== null && charHP <= 0);

    // 1. Defeat / Game Over
    if (isDead) {
        playBGMTrack("Game Over.mp3", false);
        return;
    }

    const loc = (world.current_location || 'Imperial Dungeon').trim();
    const locLower = loc.toLowerCase();
    const prov = (world.current_province || 'Cyrodiil').trim().toLowerCase();
    const stage = world.quest_stage !== undefined ? parseInt(world.quest_stage) : 10;
    const dateObj = world.date || world.tamrielic_date || {};
    const hour = dateObj.hour !== undefined ? parseInt(dateObj.hour) : 12;
    const timeOfDay = (dateObj.time_of_day || dateObj.time || '').toLowerCase();

    // 2. Boss / Climax / Imperial Palace
    if (locLower.includes("palace") && (locLower.includes("imperial") || locLower.includes("tharn") || stage >= 80)) {
        playBGMTrack("Tharn's Betrayal.mp3");
        return;
    }

    // 3. Dungeons, Crypts, Prisons, Sewers, Caves, Starting Cells
    const isDungeon = locLower.includes("dungeon") || locLower.includes("prison") ||
                      locLower.includes("sewer") || locLower.includes("crypt") ||
                      locLower.includes("catacomb") || locLower.includes("cave") ||
                      locLower.includes("cavern") || locLower.includes("lair") ||
                      locLower.includes("fang lair") || locLower.includes("labyrinthian") ||
                      locLower.includes("crypt of hearts") || locLower.includes("murkwood") ||
                      locLower.includes("dagoth ur") || locLower.includes("tomb") ||
                      locLower.includes("ruin") || locLower.includes("cell") ||
                      locLower.includes("labyrinth") || locLower.includes("keep");
    if (isDungeon) {
        playBGMTrack("Dungeon Crawling.mp3");
        return;
    }

    // 4. Specific City & Settlement Buildings / Services
    if (locLower.includes("inn") || locLower.includes("tavern") || locLower.includes("alehouse") || locLower.includes("pub")) {
        playBGMTrack("The Wandering Inn.mp3");
        return;
    }
    if (locLower.includes("mages guild") || locLower.includes("arcane academy") || locLower.includes("library") || locLower.includes("guildhall")) {
        playBGMTrack("The Mages Guild.mp3");
        return;
    }
    if (locLower.includes("forge") || locLower.includes("blacksmith") || locLower.includes("armorer")) {
        playBGMTrack("Blacksmith.mp3");
        return;
    }
    if (locLower.includes("temple") || locLower.includes("shrine") || locLower.includes("sanctuary")) {
        playBGMTrack("Arcane Arts.mp3");
        return;
    }
    if (locLower.includes("audience chamber") || locLower.includes("court") || locLower.includes("throne room")) {
        playBGMTrack("The Audience Chamber.mp3");
        return;
    }
    if (locLower.includes("thieves guild") || locLower.includes("hideout") || locLower.includes("residence") || locLower.includes("vault")) {
        playBGMTrack("Breaking And Entering.mp3");
        return;
    }
    if (locLower.includes("market") || locLower.includes("bazaar") || locLower.includes("shop") || locLower.includes("store")) {
        playBGMTrack("Where Dost Thou Hail.mp3");
        return;
    }

    // 5. Environmental & Time-of-Day Overworld
    if (locLower.includes("water") || locLower.includes("river") || locLower.includes("lake") || locLower.includes("sea") || locLower.includes("swim") || locLower.includes("bay")) {
        playBGMTrack("Swimming.mp3");
        return;
    }

    const isNight = (hour >= 21 || hour < 5) || timeOfDay.includes("night") || timeOfDay.includes("midnight") || timeOfDay.includes("curfew");
    if (isNight) {
        playBGMTrack("The Late Hours.mp3");
        return;
    }

    const isSunset = (hour >= 18 && hour < 21) || timeOfDay.includes("sunset") || timeOfDay.includes("dusk") || timeOfDay.includes("evening");
    if (isSunset) {
        playBGMTrack("Evening Star.mp3");
        return;
    }

    if (prov.includes("skyrim") || locLower.includes("snow") || locLower.includes("blizzard") || locLower.includes("frost")) {
        playBGMTrack("Winter In Hammerfell.mp3");
        return;
    }

    if (prov.includes("black marsh") || locLower.includes("marsh") || locLower.includes("swamp") || locLower.includes("bog")) {
        playBGMTrack("Foggy Afternoon.mp3");
        return;
    }

    const isWilderness = locLower.includes("wilderness") || locLower.includes("road") || locLower.includes("forest") || locLower.includes("woods") || locLower.includes("plains") || locLower.includes("travel");
    if (isWilderness) {
        playBGMTrack("The First Seed.mp3");
        return;
    }

    // 6. Default City / Settlement Daytime
    playBGMTrack("A Warm Welcome.mp3");
}

function evaluateSceneBGM(text, locationContext) {
    const combined = `${text || ''} ${locationContext || ''}`.toLowerCase();

    // Victory / Level Up / Quest Completion sting (non-looping)
    if (combined.includes("[arena_advance_stage") || combined.includes("[arena_level_up") ||
        combined.includes("objective completed") || combined.includes("quest completed") ||
        combined.includes("leveled_up") || combined.includes("gained a level") || combined.includes("victory")) {
        playBGMTrack("Objective Completed.mp3", false);
        return;
    }

    // Spectral Visions (Ria Silmane)
    if (combined.includes("ria silmane") || combined.includes("spectral vision") || combined.includes("dream vision") ||
        combined.includes("spectral form") || combined.includes("ghostly figure") || combined.includes("spirit of ria")) {
        playBGMTrack("A Vision Beyond.mp3");
        return;
    }

    // Derive directly from world state
    updateMusicFromWorldState();
}

// --- verifyConnections ---
async function verifyConnections(isSilent = false) {
    try {
        await initializeModelSelect();
        if (connectionStatus.remote_configured  || connectionStatus.local_online) {
            const onboarding = document.getElementById('onboarding-container');
            if (onboarding) onboarding.remove();
            
            let welcome = document.getElementById('welcome-message');
            if (!welcome) {
                showWelcomeMessage();
            }
            if (!isSilent) {
                // Connection verified successfully, update welcome without modal alert
            }
        } else {
            if (!isSilent) {
                showCustomAlert("Connection Failed", "Could not connect to Remote Cloud or Local LLM. Please verify credentials or check if the local server is running on port 1234.");
            }
        }
    } catch (e) {
        console.error("Error verifying connection:", e);
    }
}

// --- checkOnboardingStatus ---
function checkOnboardingStatus() {
    verifyConnections();
}

// --- checkModalStatus ---
function checkModalStatus() {
    verifyConnections();
}

/* ==========================================================================
   IV. 3. SERVER CONTROL MIDDLEWARE
   ========================================================================== */

// --- installLocalLLM ---
async function installLocalLLM(btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Installing CLI...`;
    const prog = document.getElementById('local-install-progress');
    if (prog) prog.style.display = 'block';
    try {
        const res = await fetch('/api/local_llm/install', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            // Start status polling
            pollInstallStatus(btn);
        } else {
            showCustomAlert("Installation Failed", `Failed to initiate installation: ${data.message}`);
            btn.disabled = false;
            btn.textContent = "Install llama-server";
        }
    } catch (e) {
        showCustomAlert("Error", "Error communicating with server.");
        btn.disabled = false;
        btn.textContent = "Install llama-server";
    }
}

// --- pollInstallStatus ---
function pollInstallStatus(btn) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch('/api/local_llm/status');
            const data = await res.json();
            if (data.installed) {
                clearInterval(interval);
                await startLocalLLM();
                await initializeModelSelect();
                if (document.getElementById('onboarding-container')) {
                    showOnboardingCard();
                }
                updateConnectionModalStatus();
            }
        } catch (e) {
            console.error("Error polling installation status:", e);
        }
    }, 3000);
}

// --- startLocalLLM ---
async function startLocalLLM(btn) {
    if (_localStarting) return;
    _localStarting = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Starting...`;
    }
    // Optimistic UI state
    connectionStatus.local_online = 'starting';
    updateConnectionModalStatus();
    if (document.getElementById('onboarding-container')) {
        showOnboardingCard();
    }
    try {
        const res = await fetch('/api/local_llm/start', { method: 'POST' });
        const data = await res.json();
        if (!data.success) {
            connectionStatus.local_online = false;
            showCustomAlert("Failed to Start", data.message);
        }
    } catch (e) {
        connectionStatus.local_online = false;
        showCustomAlert("Error", "Failed to initiate server start.");
    } finally {
        _localStarting = false;
        updateConnectionModalStatus();
    }
}

// --- stopLocalLLM ---
async function stopLocalLLM(btn) {
    if (_localStopping) return;
    _localStopping = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Stopping server...`;
    }
    // Optimistic UI state
    connectionStatus.local_online = 'stopping';
    updateConnectionModalStatus();
    try {
        const res = await fetch('/api/local_llm/stop', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            connectionStatus.local_online = false;
            await initializeModelSelect();
        } else {
            connectionStatus.local_online = true; // Rollback
            showCustomAlert("Failed to Stop", data.message);
        }
    } catch (e) {
        connectionStatus.local_online = true; // Rollback
        showCustomAlert("Error", "Failed to communicate with server.");
    } finally {
        _localStopping = false;
        updateConnectionModalStatus();
    }
}

// --- stopComfyUI ---
async function stopComfyUI(btn) {
    if (_comfyStopping) return;
    _comfyStopping = true;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Stopping ComfyUI...`;
    }
    // Optimistic UI state
    comfyStatus.running = 'stopping';
    updateComfyModalStatus(true);
    try {
        const res = await fetch('/api/comfy/stop', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            comfyStatus.running = false;
        } else {
            comfyStatus.running = true; // Rollback
            showCustomAlert("Failed to Stop", data.message);
        }
    } catch (e) {
        comfyStatus.running = true; // Rollback
        showCustomAlert("Error", "Failed to stop ComfyUI.");
    } finally {
        _comfyStopping = false;
        updateComfyModalStatus(true);
    }
}

// --- formatBytes helper ---
function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// --- searchHFModels ---
async function searchHFModels(inputId, resultsId) {
    const input = document.getElementById(inputId);
    const container = document.getElementById(resultsId);
    if (!input || !container) return;
    const query = input.value.trim();
    if (!query) return;

    container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem; text-align: center; width: 100%; margin: 10px 0;">Searching Hugging Face...</div>';
    try {
        const res = await fetch(`/api/local_llm/search?query=${encodeURIComponent(query)}`);
        const data = await res.json();
        const results = data.results || [];
        if (results.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem; text-align: center; width: 100%; margin: 10px 0;">No GGUF models found.</div>';
            return;
        }
        container.innerHTML = '';
        results.forEach(m => {
            const item = document.createElement('div');
            item.style.cssText = 'display: flex; flex-direction: column; padding: 10px; background: hsla(215, 5%, 100%, 0.03); border: 1px solid var(--border-color); border-radius: 8px; width: 100%; box-sizing: border-box; gap: 8px; margin-bottom: 6px;';
            item.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%;">
                    <div style="min-width: 0; flex: 1; text-align: left;">
                        <div style="font-weight: 600; font-size: 0.78rem; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${m.id}">${m.id}</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 2px;">Likes: ${m.likes} • Downloads: ${m.downloads}</div>
                    </div>
                    <button onclick="expandHFRepo('${m.id}', this)" class="onboarding-btn" style="margin: 0; padding: 2px 8px; font-size: 0.7rem; height: 24px; flex-shrink: 0; background: var(--border-color); color: var(--text-main); border: 1px solid var(--border-color); border-radius: 4px;">Show Files</button>
                </div>
                <div class="repo-files-container" style="display: none; border-top: 1px solid hsla(215, 5%, 100%, 0.05); padding-top: 8px; margin-top: 4px; flex-direction: column; gap: 6px;"></div>
            `;
            container.appendChild(item);
        });
    } catch (e) {
        container.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.75rem; text-align: center; width: 100%; margin: 10px 0;">Search failed.</div>';
    }
}

// --- expandHFRepo ---
async function expandHFRepo(repoId, btn) {
    const card = btn.closest('div').parentNode;
    const filesContainer = card.querySelector('.repo-files-container');
    if (!filesContainer) return;
    
    if (filesContainer.style.display === 'flex') {
        filesContainer.style.display = 'none';
        btn.textContent = "Show Files";
        return;
    }
    
    filesContainer.style.display = 'flex';
    filesContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.65rem; text-align: center; width: 100%; margin: 5px 0;">Loading variants...</div>';
    btn.textContent = "Hide Files";
    
    try {
        const res = await fetch(`/api/local_llm/huggingface/files?repo_id=${encodeURIComponent(repoId)}`);
        const data = await res.json();
        const files = data.files || [];
        if (files.length === 0) {
            filesContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.65rem; text-align: center; width: 100%; margin: 5px 0;">No GGUF variants found in this repo.</div>';
            return;
        }
        filesContainer.innerHTML = '';
        files.forEach(f => {
            const fileRow = document.createElement('div');
            fileRow.style.cssText = 'display: flex; flex-direction: column; font-size: 0.7rem; background: rgba(0,0,0,0.15); padding: 8px; border-radius: 6px; gap: 6px; width: 100%; box-sizing: border-box; border: 1px solid hsla(215, 5%, 100%, 0.03);';
            const trackingName = `${repoId}@${f.filename}`;
            const cleanId = trackingName.replace(/[^a-zA-Z0-9]/g, '');
            fileRow.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%;">
                    <div style="flex: 1; min-width: 0; text-align: left;">
                        <div style="font-weight: 500; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; color: var(--text-main);" title="${f.filename}">${f.filename}</div>
                        <div style="font-size: 0.62rem; color: var(--text-muted); margin-top: 1px;">Size: ${formatBytes(f.size)} • Quant: ${f.quantization || 'Unknown'}</div>
                    </div>
                    <button onclick="downloadHFModel('${repoId}', '${f.filename}', this)" class="onboarding-btn" style="margin: 0; padding: 2px 6px; font-size: 0.65rem; height: 20px; flex-shrink: 0; border-radius: 4px;">Download</button>
                </div>
                <div class="progress-wrapper-${cleanId}" style="display: none; width: 100%;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.58rem; color: var(--text-muted); margin-bottom: 2px; width: 100%;">
                        <span class="pct-span">0%</span>
                        <span class="speed-span">0 MB/s</span>
                        <span class="eta-span">--:--</span>
                    </div>
                    <div style="background: hsla(215, 5%, 100%, 0.08); border-radius: 3px; height: 4px; overflow: hidden; width: 100%;">
                        <div class="bar-span" style="background: var(--primary-accent); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                    </div>
                </div>
            `;
            filesContainer.appendChild(fileRow);
        });
    } catch (e) {
        filesContainer.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.65rem; text-align: center; width: 100%; margin: 5px 0;">Failed to load files.</div>';
    }
}

// --- downloadHFModel ---
async function downloadHFModel(repoId, quantization, btn) {
    btn.disabled = true;
    btn.textContent = "Requesting...";
    const trackingName = `${repoId}@${quantization}`;
    const cleanId = trackingName.replace(/[^a-zA-Z0-9]/g, '');
    const row = btn.closest('div').parentNode;
    const progressWrapper = row.querySelector(`.progress-wrapper-${cleanId}`);
    if (progressWrapper) progressWrapper.style.display = 'block';

    try {
        const res = await fetch('/api/local_llm/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: repoId, quantization: quantization })
        });
        const data = await res.json();
        if (data.success) {
            btn.textContent = "Downloading...";
            pollDownloadProgress(trackingName, progressWrapper, btn);
        } else {
            showCustomAlert("Download Failed", data.error || data.message || "Failed to start download.");
            btn.disabled = false;
            btn.textContent = "Download";
            if (progressWrapper) progressWrapper.style.display = 'none';
        }
    } catch (e) {
        showCustomAlert("Error", "Failed to connect to server.");
        btn.disabled = false;
        btn.textContent = "Download";
        if (progressWrapper) progressWrapper.style.display = 'none';
    }
}

// --- pollDownloadProgress ---
function pollDownloadProgress(trackingName, progressWrapper, btn) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch('/api/local_llm/status');
            const data = await res.json();
            const statusObj = data.download_status[trackingName];
            if (statusObj) {
                const pctSpan = progressWrapper.querySelector('.pct-span');
                const speedSpan = progressWrapper.querySelector('.speed-span');
                const etaSpan = progressWrapper.querySelector('.eta-span');
                const barSpan = progressWrapper.querySelector('.bar-span');

                if (statusObj.status === 'downloading') {
                    const downloaded = statusObj.downloaded_bytes || 0;
                    const total = statusObj.total_size_bytes || 1;
                    const percent = (downloaded / total * 100).toFixed(1);
                    const speed = ((statusObj.bytes_per_second || 0) / 1024 / 1024).toFixed(2);
                    
                    if (pctSpan) pctSpan.textContent = `${percent}%`;
                    if (speedSpan) speedSpan.textContent = `${speed} MB/s`;
                    if (barSpan) barSpan.style.width = `${percent}%`;

                    if (statusObj.estimated_completion && etaSpan) {
                        const remainingMs = new Date(statusObj.estimated_completion) - new Date();
                        const remainingSec = Math.max(0, Math.floor(remainingMs / 1000));
                        const min = Math.floor(remainingSec / 60);
                        const sec = remainingSec % 60;
                        etaSpan.textContent = `ETA: ${min}m ${sec}s`;
                    }
                } else if (statusObj.status === 'completed') {
                    clearInterval(interval);
                    btn.textContent = "Downloaded";
                    btn.style.background = "var(--success-color)"; // green style
                    btn.disabled = true;
                    if (pctSpan) pctSpan.textContent = "100%";
                    if (barSpan) barSpan.style.width = "100%";
                    if (etaSpan) etaSpan.textContent = "Finished";
                    await initializeModelSelect();
                    fetchAndRenderLocalModels();
                } else if (statusObj.status === 'failed') {
                    clearInterval(interval);
                    showCustomAlert("Download Failed", `Model download failed:<br><code style="color: var(--danger-bright); font-size: 0.75rem;">${statusObj.error || 'Unknown error'}</code>`);
                    btn.disabled = false;
                    btn.textContent = "Download";
                    if (progressWrapper) progressWrapper.style.display = 'none';
                }
            }
        } catch (e) {
            console.error("Error polling download progress:", e);
        }
    }, 2000);
}

// --- fetchAndRenderLocalModels ---
async function fetchAndRenderLocalModels() {
    const listContainer = document.getElementById('modal-local-models-list');
    if (!listContainer) return;
    
    if (!listContainer.innerHTML.trim()) {
        listContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 10px;">Loading downloaded models...</div>';
    }
    try {
        const res = await fetch('/api/local_llm/status');
        const data = await res.json();
        
        const downloaded = data.downloaded_models || [];
        const loaded = data.loaded_models || [];
        
        // Filter out embedding models from display list
        const chatModels = downloaded.filter(m => !(m.toLowerCase().includes("embed") || m.toLowerCase().includes("nomic")));
        
        if (chatModels.length === 0) {
            listContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px;">No downloaded chat models found on disk.</div>';
            return;
        }
        
        let html = '<div style="margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px; text-align: left;">';
        html += '<div style="font-size: 0.8rem; font-weight: 600; color: var(--text-color); margin-bottom: 8px;">Manage Downloaded Models:</div>';
        html += '<div style="display: flex; flex-direction: column; gap: 8px; max-height: 160px; overflow-y: auto; padding-right: 4px; box-sizing: border-box;">';
        
        chatModels.forEach(modelKey => {
            const displayName = modelKey.includes('/') ? modelKey.split('/').pop() : modelKey;
            
            // Check if this model (or a close variant) is loaded
            const isLoaded = loaded.some(loadedVal => {
                const loadedNorm = loadedVal.toLowerCase().replace(".gguf", "").replace(/[^a-z0-9]/g, "");
                const downloadedNorm = modelKey.toLowerCase().replace(".gguf", "").replace(/[^a-z0-9]/g, "");
                return downloadedNorm.includes(loadedNorm) || loadedNorm.includes(downloadedNorm);
            });
            
            html += `
                <div style="display: flex; align-items: center; justify-content: space-between; background: hsla(215, 5%, 100%, 0.03); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); gap: 10px;">
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-size: 0.78rem; font-weight: 500; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${displayName}">${displayName}</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${modelKey}</div>
                    </div>
                    <div style="display: flex; gap: 6px;">
                        ${isLoaded ? 
                            `<button onclick="unloadLocalModel('${modelKey.replace(/\\/g, '\\\\')}', this)" class="onboarding-btn" style="margin: 0; padding: 4px 8px; font-size: 0.7rem; border-radius: 4px;">Unload</button>` : 
                            `<button onclick="loadLocalModelDirect('${modelKey.replace(/\\/g, '\\\\')}', this)" class="onboarding-btn" style="margin: 0; padding: 4px 8px; font-size: 0.7rem; border-radius: 4px;">Load</button>`
                        }
                        <button onclick="deleteLocalModel('${modelKey.replace(/\\/g, '\\\\')}', this)" class="onboarding-btn" style="margin: 0; padding: 4px 8px; font-size: 0.7rem; border-radius: 4px;">Delete</button>
                    </div>
                </div>
            `;
        });
        
        html += '</div></div>';
        listContainer.innerHTML = html;
    } catch (e) {
        console.error("Error fetching local models detail:", e);
        listContainer.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.75rem; margin-top: 10px;">Failed to fetch model list.</div>';
    }
}

// --- unloadLocalModel ---
async function unloadLocalModel(modelKey, btn) {
    btn.disabled = true;
    btn.textContent = "Unloading...";
    try {
        const res = await fetch('/api/local_llm/unload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelKey })
        });
        const data = await res.json();
        if (data.success) {
            await initializeModelSelect();
            fetchAndRenderLocalModels();
        } else {
            showCustomAlert("Error", data.message || "Failed to unload model.");
            btn.disabled = false;
            btn.textContent = "Unload";
        }
    } catch (e) {
        console.error(e);
        btn.disabled = false;
        btn.textContent = "Unload";
    }
}

// --- loadLocalModelDirect ---
async function loadLocalModelDirect(modelKey, btn) {
    btn.disabled = true;
    btn.textContent = "Loading...";
    try {
        const res = await fetch('/api/local_llm/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelKey })
        });
        const data = await res.json();
        if (data.success) {
            await initializeModelSelect();
            fetchAndRenderLocalModels();
        } else {
            showCustomAlert("Error", data.message || "Failed to load model.");
            btn.disabled = false;
            btn.textContent = "Load";
        }
    } catch (e) {
        console.error(e);
        btn.disabled = false;
        btn.textContent = "Load";
    }
}

// --- deleteLocalModel ---
async function deleteLocalModel(modelKey, btn) {
    showCustomConfirm("Delete Model", `Are you sure you want to permanently delete this model from disk?<br><code style="font-size: 0.7rem; color: var(--danger-bright); word-break: break-all;">${modelKey}</code>`, async () => {
        btn.disabled = true;
        btn.textContent = "Deleting...";
        try {
            const res = await fetch('/api/local_llm/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelKey })
            });
            const data = await res.json();
            if (data.success) {
                await initializeModelSelect();
                fetchAndRenderLocalModels();
            } else {
                showCustomAlert("Error", data.message || "Failed to delete model.");
                btn.disabled = false;
                btn.textContent = "Delete";
            }
        } catch (e) {
            console.error(e);
            btn.disabled = false;
            btn.textContent = "Delete";
        }
    });
}

// --- downloadComfyCheckpoint ---
async function downloadComfyCheckpoint(url, filename, btn) {
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Starting...";
    }
    try {
        const res = await fetch('/api/comfy/checkpoints/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, filename: filename })
        });
        const data = await res.json();
        if (data.success) {
            pollComfyCheckpointDownloads();
        } else {
            showCustomAlert("Error", data.message || "Failed to start download");
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Download";
            }
        }
    } catch (e) {
        showCustomAlert("Error", "Connection error. Failed to start download.");
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Download";
        }
    }
}

// --- pollComfyCheckpointDownloads ---
async function pollComfyCheckpointDownloads() {
    try {
        const res = await fetch('/api/comfy/checkpoints/download_status');
        const status = await res.json();
        
        const container = document.getElementById('comfy-checkpoint-downloads-container');
        const list = document.getElementById('comfy-checkpoint-downloads-list');
        if (!container || !list) return;
        
        const filenames = Object.keys(status);
        let activeCount = 0;
        
        if (filenames.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        let html = '';
        filenames.forEach(filename => {
            const info = status[filename];
            if (info.status === 'downloading') {
                activeCount++;
                html += `
                    <div style="background: hsla(215, 5%, 100%, 0.02); border: 1px solid var(--border-color); padding: 6px; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="font-weight: 500; font-size: 0.72rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 70%;" title="${filename}">${filename}</span>
                            <span>${info.progress}%</span>
                        </div>
                        <div style="width: 100%; height: 4px; background: hsla(215, 5%, 100%, 0.1); border-radius: 2px; overflow: hidden;">
                            <div style="width: ${info.progress}%; height: 100%; background: var(--primary-accent); transition: width 0.3s;"></div>
                        </div>
                    </div>
                `;
            } else if (info.status === 'completed') {
                html += `
                    <div style="background: hsla(115, 70%, 45%, 0.05); border: 1px solid hsla(115, 70%, 45%, 0.2); padding: 6px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.72rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 80%; color: var(--success-bright);" title="${filename}">${filename}</span>
                        <span style="color: var(--success-bright); font-size: 0.65rem; font-weight: 600;">Done</span>
                    </div>
                `;
            } else if (info.status === 'failed') {
                html += `
                    <div style="background: hsla(0, 85%, 60%, 0.05); border: 1px solid hsla(0, 85%, 60%, 0.2); padding: 6px; border-radius: 4px;">
                        <div style="font-size: 0.72rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; color: var(--danger-bright);" title="${filename}">${filename}</div>
                        <div style="font-size: 0.62rem; color: var(--danger-bright); margin-top: 2px;">Error: ${info.error || 'Failed'}</div>
                    </div>
                `;
            }
        });
        
        list.innerHTML = html;
        container.style.display = 'block';
        
        if (activeCount > 0) {
            if (comfyDownloadTimer) clearTimeout(comfyDownloadTimer);
            comfyDownloadTimer = setTimeout(pollComfyCheckpointDownloads, 2000);
        } else {
            fetchComfyCheckpoints();
        }
    } catch (e) {
        console.error("Error polling comfy checkpoint downloads:", e);
    }
}

// --- installComfyUI ---
async function installComfyUI(btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Starting installation...`;
    try {
        const res = await fetch('/api/comfy/install', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            // Update state immediately to show progress bar and start background polling
            updateComfyModalStatus();
        } else {
            showCustomAlert("Installation Failed", data.message);
            btn.disabled = false;
            btn.textContent = "Auto-Install ComfyUI";
        }
    } catch (e) {
        showCustomAlert("Error", "Failed to contact backend.");
        btn.disabled = false;
        btn.textContent = "Auto-Install ComfyUI";
    }
}

// --- startComfyUI ---
async function startComfyUI(btn) {
    if (_comfyStarting) return;
    _comfyStarting = true;
    // Optimistic UI state
    comfyStatus.running = 'starting';
    updateComfyModalStatus(true);
    if (document.getElementById('onboarding-container')) {
        showOnboardingCard();
    }
    try {
        const res = await fetch('/api/comfy/start', { method: 'POST' });
        const data = await res.json();
        if (!data.success) {
            comfyStatus.running = false;
            showCustomAlert("Failed to Start", data.message);
        }
    } catch (e) {
        comfyStatus.running = false;
        showCustomAlert("Error", "Failed to start ComfyUI.");
    } finally {
        _comfyStarting = false;
        updateComfyModalStatus(true);
    }
}

// --- resolveWorkflowDependencies ---
async function resolveWorkflowDependencies(btn) {
    if (_comfyResolving) return;
    _comfyResolving = true;
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin" style="display: inline-block; width: 14px; height: 14px; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>Analyzing Workflow...`;
    try {
        const res = await fetch('/api/comfy/resolve_workflow', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({}) 
        });
        const data = await res.json();
        if (data.success) {
            updateComfyModalStatus();
        } else {
            showCustomAlert("Resolution Failed", data.error || data.message);
            btn.disabled = false;
            btn.textContent = "Resolve Workflow Dependencies";
        }
    } catch (e) {
        showCustomAlert("Error", "Failed to trigger dependency resolution.");
        btn.disabled = false;
        btn.textContent = "Resolve Workflow Dependencies";
    } finally {
        _comfyResolving = false;
    }
}

/* ==========================================================================
   V. 4. DYNAMIC UI ACCESSORIES & PROMPTS
   ========================================================================== */

// ── Arena: Player Character Status & Heart Controller ─────────────────────
let currentCharacterData = null;

async function fetchCharacterStatus() {
    try {
        const res = await fetch('/api/character/status?t=' + Date.now());
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'success' && data.character) {
            currentCharacterData = data;
            if (data.character.name) {
                activePlayerName = data.character.name;
            }
            updatePlayerHeartState(data.character, data.world);
            renderCharacterStatusModal(data);
            updateMusicFromWorldState(data.world, data.character?.vitals || data.character?.derived);
        }
    } catch (e) {
        console.warn('Error fetching character status:', e);
    }
}

let _lastTrackedVitals = {
    hp: null,
    hpMax: null,
    mp: null,
    mpMax: null,
    stamina: null,
    staminaMax: null,
    gold: null,
    itemCount: null,
    itemNames: []
};

function updateInputResourceBars() {
    const barContainer = document.getElementById('input-resource-bars');
    if (!barContainer) return;

    const curHp = _lastTrackedVitals.hp !== null ? _lastTrackedVitals.hp : 28;
    const curHpMax = _lastTrackedVitals.hpMax || 28;
    const curMp = _lastTrackedVitals.mp !== null ? _lastTrackedVitals.mp : 42;
    const curMpMax = _lastTrackedVitals.mpMax || 42;
    const curSp = _lastTrackedVitals.stamina !== null ? _lastTrackedVitals.stamina : 50;
    const curSpMax = _lastTrackedVitals.staminaMax || 50;

    const hpPct = Math.max(0, Math.min(100, (curHp / (curHpMax || 1)) * 100));
    const mpPct = Math.max(0, Math.min(100, (curMp / (curMpMax || 1)) * 100));
    const spPct = Math.max(0, Math.min(100, (curSp / (curSpMax || 1)) * 100));

    let mpBar = barContainer.querySelector('.resource-bar.magicka');
    let hpBar = barContainer.querySelector('.resource-bar.health');
    let spBar = barContainer.querySelector('.resource-bar.stamina');

    if (!mpBar || !hpBar || !spBar) {
        barContainer.innerHTML = `
            <div class="resource-bar magicka" title="Magicka: ${Math.round(curMp)} / ${Math.round(curMpMax)}">
                <div class="resource-bar-track">
                    <div class="resource-bar-fill magicka" style="width: ${mpPct}%;"></div>
                </div>
            </div>
            <div class="resource-bar health" title="Health: ${Math.round(curHp)} / ${Math.round(curHpMax)}">
                <div class="resource-bar-track">
                    <div class="resource-bar-fill health" style="width: ${hpPct}%;"></div>
                </div>
            </div>
            <div class="resource-bar stamina" title="Stamina: ${Math.round(curSp)} / ${Math.round(curSpMax)}">
                <div class="resource-bar-track">
                    <div class="resource-bar-fill stamina" style="width: ${spPct}%;"></div>
                </div>
            </div>
        `;
    } else {
        mpBar.title = `Magicka: ${Math.round(curMp)} / ${Math.round(curMpMax)}`;
        const mpFill = mpBar.querySelector('.resource-bar-fill');
        if (mpFill) mpFill.style.width = `${mpPct}%`;

        hpBar.title = `Health: ${Math.round(curHp)} / ${Math.round(curHpMax)}`;
        const hpFill = hpBar.querySelector('.resource-bar-fill');
        if (hpFill) hpFill.style.width = `${hpPct}%`;

        spBar.title = `Stamina: ${Math.round(curSp)} / ${Math.round(curSpMax)}`;
        const spFill = spBar.querySelector('.resource-bar-fill');
        if (spFill) spFill.style.width = `${spPct}%`;
    }
}

function triggerInputPulse(pulseType) {
    if (!pulseType) return;
    const inputWrapper = document.querySelector('.input-wrapper');
    if (!inputWrapper) return;

    const pulseClass = `input-pulse-${pulseType}`;
    inputWrapper.classList.remove(pulseClass);
    void inputWrapper.offsetWidth;
    inputWrapper.classList.add(pulseClass);
    setTimeout(() => {
        inputWrapper.classList.remove(pulseClass);
    }, 850);
}

function triggerBagPulse() {
    const bagBtn = document.querySelector('.inventory-btn');
    if (!bagBtn) return;
    bagBtn.classList.remove('bag-pulse');
    void bagBtn.offsetWidth;
    bagBtn.classList.add('bag-pulse');
    setTimeout(() => {
        bagBtn.classList.remove('bag-pulse');
    }, 900);
}

function updatePlayerHeartState(char, world) {
    const heartElement = document.getElementById('header-heart-pulse') || document.querySelector('.heart-pulse');
    if (!heartElement || !char || !char.derived) return;

    const d = char.derived;
    const hpCurrent = d.hp_current !== undefined ? d.hp_current : 28;
    const hpMax = d.hp_max || 28;
    const mpCurrent = d.mp_current !== undefined ? d.mp_current : (d.sp_current !== undefined ? d.sp_current : 42);
    const mpMax = d.mp_max || (d.sp_max !== undefined ? d.sp_max : 42);
    const staminaCurrent = d.stamina_current !== undefined ? d.stamina_current : 50;
    const staminaMax = d.stamina_max || 50;
    const goldCurrent = char.gold !== undefined ? char.gold : 0;
    const inventory = char.inventory || [];
    const currentItemCount = inventory.reduce((sum, item) => sum + (item.quantity || 1), 0);

    // Trigger input wrapper glow pulse on resource changes
    if (_lastTrackedVitals.hp !== null) {
        const dHp = hpCurrent - _lastTrackedVitals.hp;
        const dMp = mpCurrent - _lastTrackedVitals.mp;
        const dStamina = staminaCurrent - _lastTrackedVitals.stamina;
        const dGold = (_lastTrackedVitals.gold !== null && goldCurrent !== undefined) ? (goldCurrent - _lastTrackedVitals.gold) : 0;
        const dItems = (_lastTrackedVitals.itemCount !== null) ? (currentItemCount - _lastTrackedVitals.itemCount) : 0;

        if (dHp !== 0) {
            triggerInputPulse(dHp > 0 ? 'hp-up' : 'hp-down');
        } else if (dMp !== 0) {
            triggerInputPulse('mp');
        } else if (dStamina !== 0) {
            triggerInputPulse('sp');
        }
        
        if (dItems !== 0) {
            triggerBagPulse();
        }
    }

    _lastTrackedVitals.hp = hpCurrent;
    _lastTrackedVitals.hpMax = hpMax;
    _lastTrackedVitals.mp = mpCurrent;
    _lastTrackedVitals.mpMax = mpMax;
    _lastTrackedVitals.stamina = staminaCurrent;
    _lastTrackedVitals.staminaMax = staminaMax;
    _lastTrackedVitals.gold = goldCurrent;
    _lastTrackedVitals.itemCount = currentItemCount;
    _lastTrackedVitals.itemNames = inventory.map(it => it.name);

    updateInputResourceBars();

    const hpPct = Math.max(0, Math.min(100, (hpCurrent / hpMax) * 100));
    const conditions = (char.conditions || []).map(c => c.toLowerCase());
    const isAfflicted = conditions.some(c => c.includes('poison') || c.includes('disease'));

    let color = 'var(--danger-vivid)'; // Crimson Red
    let glow = 'hsla(0, 85%, 60%, 0.6)';
    let speed = '2.0s';
    let statusText = `Vitality: ${hpCurrent}/${hpMax} HP (Healthy)`;

    if (hpCurrent <= 0) {
        color = 'var(--text-muted)'; // Slate gray (fallen)
        glow = 'hsla(215, 18%, 47%, 0.4)';
        speed = '4.0s';
        statusText = 'Player Status: Fallen (GAME OVER)';
        heartElement.classList.remove('jiggling');
        triggerGameOverState();
    } else {
        if (typeof isGameOverState !== 'undefined' && isGameOverState) {
            clearGameOverState();
        }
        if (isAfflicted) {
            color = 'var(--success-deep)'; // Sickly green (poison/disease)
            glow = 'hsla(115, 70%, 45%, 0.7)';
            speed = '0.9s';
            statusText = `Player Status: Afflicted (${char.conditions.join(', ')}) - ${hpCurrent}/${hpMax} HP`;
            heartElement.classList.remove('jiggling');
        } else if (hpPct <= 25) {
            color = 'var(--danger-deep)'; // Deep pulsing red (critical)
            glow = 'hsla(0, 74%, 51%, 0.9)';
            speed = '0.5s';
            statusText = `Player Status: Critical Health! (${hpCurrent}/${hpMax} HP)`;
            heartElement.classList.add('jiggling');
        } else if (hpPct <= 60) {
            color = 'var(--danger-color)'; // Soft wounded red
            glow = 'hsla(0, 90%, 71%, 0.7)';
            speed = '1.2s';
            statusText = `Player Status: Wounded (${hpCurrent}/${hpMax} HP)`;
            heartElement.classList.remove('jiggling');
        } else {
            color = 'var(--danger-vivid)'; // Classic Vibrant Crimson Red
            glow = 'hsla(0, 85%, 60%, 0.6)';
            speed = '2.0s';
            statusText = `Player Status: Healthy (${hpCurrent}/${hpMax} HP)`;
            heartElement.classList.remove('jiggling');
        }
    }

    heartElement.style.setProperty('--heart-color', color);
    heartElement.style.setProperty('--heart-glow', glow);
    heartElement.style.setProperty('--heart-speed', speed);
    heartElement.style.setProperty('--heart-speed-active', '0.6s');
    heartElement.title = "Player Status";
}

let isGameOverState = false;

function triggerGameOverState() {
    isGameOverState = true;
    
    const inputEl = document.getElementById('user-input');
    if (inputEl) {
        inputEl.disabled = true;
        inputEl.placeholder = "...";
        inputEl.classList.add('user-input-frozen');
    }
    
    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.style.opacity = '0.25';
        sendBtn.style.pointerEvents = 'none';
    }

    const autoGenBtn = document.getElementById('auto-generate-user-btn');
    if (autoGenBtn) {
        autoGenBtn.disabled = true;
        autoGenBtn.style.opacity = '0.25';
        autoGenBtn.style.pointerEvents = 'none';
    }

    const diceBtn = document.getElementById('dice-skill-btn');
    if (diceBtn) {
        diceBtn.disabled = true;
        diceBtn.style.opacity = '0.25';
        diceBtn.style.pointerEvents = 'none';
    }

    let banner = document.getElementById('game-over-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'game-over-banner';
        banner.className = 'game-over-overlay';
        banner.innerHTML = `
            <div class="game-over-card">
                <div class="game-over-skull">💀</div>
                <h2 class="game-over-title">GAME OVER</h2>
            </div>
        `;
        const container = document.getElementById('chat-container');
        if (container) {
            container.appendChild(banner);
            container.scrollTop = container.scrollHeight;
        }
    }
}

function clearGameOverState() {
    isGameOverState = false;
    const banner = document.getElementById('game-over-banner');
    if (banner) banner.remove();

    const inputEl = document.getElementById('user-input');
    if (inputEl) {
        inputEl.disabled = false;
        inputEl.placeholder = "What do you do?";
        inputEl.classList.remove('user-input-frozen');
    }

    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.style.opacity = '';
        sendBtn.style.pointerEvents = '';
    }

    const autoGenBtn = document.getElementById('auto-generate-user-btn');
    if (autoGenBtn) {
        autoGenBtn.disabled = false;
        autoGenBtn.style.opacity = '';
        autoGenBtn.style.pointerEvents = '';
    }

    const diceBtn = document.getElementById('dice-skill-btn');
    if (diceBtn) {
        diceBtn.disabled = false;
        diceBtn.style.opacity = '';
        diceBtn.style.pointerEvents = '';
    }
}

function updateHeartState() {
    fetchCharacterStatus();
}

function triggerHeartBurst() {
    // Legacy no-op stub
}

function openStatusModal() {
    fetchCharacterStatus().then(() => {
        const modal = document.getElementById('status-modal');
        if (modal) modal.style.display = 'flex';
    });
}

function closeStatusModal() {
    const modal = document.getElementById('status-modal');
    if (modal) modal.style.display = 'none';
}

function openInventoryModal() {
    fetchCharacterStatus().then(() => {
        const modal = document.getElementById('inventory-modal');
        if (modal) modal.style.display = 'flex';
    });
}

function closeInventoryModal() {
    const modal = document.getElementById('inventory-modal');
    if (modal) modal.style.display = 'none';
}

function formatTamrielicTime(hour) {
    if (hour === undefined || hour === null) return "";
    const h = parseInt(hour, 10) % 24;
    const period = h >= 12 ? "PM" : "AM";
    const displayHour = h % 12 === 0 ? 12 : h % 12;
    return `${displayHour}:00 ${period}`;
}

function renderCharacterStatusModal(data) {
    if (!data || !data.character) return;
    const char = data.character;
    const d = char.derived || {};
    const world = data.world || {};
    const mods = data.modifiers || {};

    // Header info
    const nameEl = document.getElementById('modal-char-name');
    if (nameEl) nameEl.textContent = char.name || 'Eternal Champion';

    const subEl = document.getElementById('modal-char-subtitle');
    if (subEl) subEl.textContent = `${char.race || 'Nord'} ${char.gender || 'Male'} ${char.class || 'Mage'} • Level ${char.level || 1}`;

    // Location & Date
    const locEl = document.getElementById('modal-char-location');
    if (locEl) locEl.textContent = `${world.current_location || 'Imperial Dungeon'}, ${world.current_province || 'Cyrodiil'}`;

    const dateEl = document.getElementById('modal-char-date');
    if (dateEl) {
        const tDate = world.date || world.tamrielic_date || { day: 1, month: "Morning Star", year: 389, hour: 6 };
        const timeStr = tDate.hour !== undefined ? ` • ${formatTamrielicTime(tDate.hour)}` : "";
        dateEl.textContent = `${tDate.day || 1} ${tDate.month || 'Morning Star'}, ${tDate.year ? `3E ${tDate.year}` : '3E 389'}${timeStr}`;
    }



    // HP, MP & Stamina
    const hpCurrent = d.hp_current !== undefined ? d.hp_current : 28;
    const hpMax = d.hp_max || 28;
    const hpPct = Math.max(0, Math.min(100, (hpCurrent / hpMax) * 100));

    const mpCurrent = d.mp_current !== undefined ? d.mp_current : (d.sp_current !== undefined ? d.sp_current : 42);
    const mpMax = d.mp_max || d.sp_max || 42;
    const mpPct = Math.max(0, Math.min(100, (mpCurrent / mpMax) * 100));

    const stmCurrent = d.stamina_current !== undefined ? d.stamina_current : 50;
    const stmMax = d.stamina_max || 50;
    const stmPct = Math.max(0, Math.min(100, (stmCurrent / stmMax) * 100));

    const hpText = document.getElementById('modal-char-hp-text');
    if (hpText) hpText.textContent = `${hpCurrent} / ${hpMax}`;
    const hpBar = document.getElementById('modal-char-hp-bar');
    if (hpBar) hpBar.style.width = `${hpPct}%`;

    const mpText = document.getElementById('modal-char-mp-text') || document.getElementById('modal-char-sp-text');
    if (mpText) mpText.textContent = `${mpCurrent} / ${mpMax}`;
    const mpBar = document.getElementById('modal-char-mp-bar') || document.getElementById('modal-char-sp-bar');
    if (mpBar) mpBar.style.width = `${mpPct}%`;

    const stmText = document.getElementById('modal-char-stamina-text');
    if (stmText) stmText.textContent = `${stmCurrent} / ${stmMax}`;
    const stmBar = document.getElementById('modal-char-stamina-bar');
    if (stmBar) stmBar.style.width = `${stmPct}%`;

    // Armor, Gold, XP
    const armorEl = document.getElementById('modal-char-armor');
    if (armorEl) armorEl.textContent = d.armor_rating !== undefined ? d.armor_rating : 4;

    const goldEl = document.getElementById('modal-char-gold');
    if (goldEl) {
        goldEl.textContent = `${char.gold !== undefined ? char.gold : 75}`;
        goldEl.style.removeProperty('color');
    }

    const invGoldEl = document.getElementById('inventory-gold-display');
    if (invGoldEl) {
        const currentGold = char.gold !== undefined ? char.gold : 0;
        invGoldEl.innerHTML = `<span onclick="promptModifyGold()" title="Edit Gold" style="cursor: pointer; user-select: none; transition: transform 0.15s ease; display: inline-flex; align-items: center; justify-content: center; margin-right: 6px; line-height: 1; vertical-align: middle;" onmouseenter="this.style.transform='scale(1.25)'" onmouseleave="this.style.transform='scale(1.0)'">🪙</span><span style="line-height: 1; display: inline-flex; align-items: center;">${currentGold} Gold</span>`;
    }

    const xpEl = document.getElementById('modal-char-xp');
    if (xpEl) xpEl.textContent = `${char.experience || 0}`;

    // Attributes — Canonical Elder Scrolls Order: STR, INT, WIL, AGI, SPD, END, PER, LUC
    const attrContainer = document.getElementById('modal-char-attributes');
    if (attrContainer && char.attributes) {
        attrContainer.innerHTML = '';
        const TES_ATTR_ORDER = ['strength', 'intelligence', 'willpower', 'agility', 'speed', 'endurance', 'personality', 'luck'];
        TES_ATTR_ORDER.forEach(attr => {
            const val = char.attributes[attr] !== undefined ? char.attributes[attr] : 50;
            const card = document.createElement('div');
            card.style.cssText = 'background: rgba(0,0,0,0.35); border: 1px solid var(--border-color); border-radius: 8px; padding: 8px 4px; text-align: center;';
            const mod = mods[attr] || '+0';
            card.innerHTML = `
                <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;">${attr.slice(0, 3)}</div>
                <div style="font-size: 1rem; font-weight: 700; color: var(--text-main); margin-top: 2px;">${val}</div>
                <div style="font-size: 0.72rem; color: var(--primary-accent); margin-top: 2px; font-weight: 600;">${mod}</div>
            `;
            attrContainer.appendChild(card);
        });
    }

    // Inventory
    const invContainer = document.getElementById('modal-char-inventory');
    if (invContainer) {
        invContainer.innerHTML = '';
        const items = char.inventory || [];
        const itemCountEl = document.getElementById('inventory-item-count');
        if (itemCountEl) itemCountEl.textContent = `${items.length} ${items.length === 1 ? 'item' : 'items'}`;

        const weight = d.encumbrance_current !== undefined ? d.encumbrance_current : 0.0;
        const maxWeight = d.encumbrance_max !== undefined ? d.encumbrance_max : 100.0;
        const isEncumbered = !!d.is_encumbered || weight > maxWeight;
        const weightEl = document.getElementById('inventory-weight-display');
        if (weightEl) {
            weightEl.textContent = `${weight} / ${maxWeight} kg`;
            if (isEncumbered) {
                weightEl.style.color = 'var(--danger-vivid)';
                weightEl.style.borderColor = 'hsla(0, 85%, 60%, 0.4)';
                weightEl.style.background = 'hsla(0, 85%, 60%, 0.15)';
                weightEl.textContent += ' (ENCUMBERED)';
            } else {
                weightEl.style.color = 'var(--text-muted)';
                weightEl.style.borderColor = 'hsla(215, 5%, 100%, 0.1)';
                weightEl.style.background = 'hsla(215, 5%, 100%, 0.06)';
            }
        }

        if (items.length === 0) {
            invContainer.innerHTML = '<span style="font-size: 0.8rem; color: var(--text-muted);">Empty — no items in your pack</span>';
        } else {
            items.forEach(item => {
                const itemRow = document.createElement('div');
                const isEq = !!item.equipped;
                const nameLower = (item.name || '').toLowerCase();
                const typeLower = (item.type || '').toLowerCase();
                const isTorch = nameLower.includes('torch') || nameLower.includes('lantern') || typeLower === 'torch' || typeLower === 'light';
                const isJewelry = nameLower.includes('ring') || nameLower.includes('amulet') || nameLower.includes('necklace') || typeLower === 'ring' || typeLower === 'neck';
                const canEquip = isTorch || isJewelry || ['weapon', '2h_weapon', 'armor', 'robes', 'shield', 'head', 'helmet', 'hood', 'hands', 'feet', 'boots', 'apparel', 'cloak', 'cape', 'mantle', 'back'].includes(typeLower) || nameLower.includes('dagger') || nameLower.includes('sword') || nameLower.includes('staff') || nameLower.includes('bow') || nameLower.includes('robe') || nameLower.includes('cuirass') || nameLower.includes('boot') || nameLower.includes('shoe') || nameLower.includes('greave') || nameLower.includes('glove') || nameLower.includes('gauntlet') || nameLower.includes('bracer') || nameLower.includes('helm') || nameLower.includes('hood') || nameLower.includes('cap') || nameLower.includes('armor') || nameLower.includes('tunic') || nameLower.includes('mail') || nameLower.includes('cloak') || nameLower.includes('cape') || nameLower.includes('mantle') || nameLower.includes('back');
                
                itemRow.style.cssText = `display: inline-flex; align-items: center; gap: 6px; background: ${isEq ? 'hsla(42, 75%, 50%, 0.12)' : 'hsla(215, 5%, 100%, 0.04)'}; border: 1px solid ${isEq ? 'hsla(42, 75%, 50%, 0.4)' : 'hsla(215, 5%, 100%, 0.08)'}; border-radius: 8px; padding: 4px 6px 4px 10px; transition: all 0.15s ease;`;
                
                if (canEquip) {
                    itemRow.style.cursor = 'pointer';
                    itemRow.title = isEq ? `Click to unequip ${item.name}` : `Click to equip ${item.name}`;
                    itemRow.onmouseover = () => {
                        itemRow.style.background = isEq ? 'hsla(42, 75%, 50%, 0.22)' : 'hsla(215, 5%, 100%, 0.08)';
                        itemRow.style.borderColor = isEq ? 'hsla(42, 75%, 50%, 0.6)' : 'hsla(215, 5%, 100%, 0.2)';
                    };
                    itemRow.onmouseout = () => {
                        itemRow.style.background = isEq ? 'hsla(42, 75%, 50%, 0.12)' : 'hsla(215, 5%, 100%, 0.04)';
                        itemRow.style.borderColor = isEq ? 'hsla(42, 75%, 50%, 0.4)' : 'hsla(215, 5%, 100%, 0.08)';
                    };
                    itemRow.onclick = () => {
                        toggleItemEquip(item.name, isEq);
                    };
                }
                
                const qtyStr = item.quantity && item.quantity > 1 ? ` x${item.quantity}` : '';
                const itemWtStr = item.weight ? ` (${item.weight} kg)` : '';
                const slotLabel = item.equipped_slot ? item.equipped_slot.replace('_', ' ').toUpperCase() : 'EQUIPPED';
                const tag = isEq ? `<span style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; background: hsla(var(--gold-h), var(--gold-s), 45%, 0.22); color: var(--text-bright); border: 1px solid var(--border-color); font-weight: 700; letter-spacing: 0.03em;">${slotLabel}</span>` : (canEquip ? '<span style="font-size: 0.65rem; color: var(--text-muted);">[Equip]</span>' : '');
                
                const equipLabel = document.createElement('div');
                equipLabel.style.cssText = `background: transparent; border: none; padding: 0; font-size: 0.82rem; color: ${isEq ? 'var(--primary-accent)' : 'var(--text-bright)'}; display: inline-flex; align-items: center; gap: 6px;`;
                equipLabel.innerHTML = `<span>${item.name}${qtyStr}${itemWtStr}</span> ${tag}`;
                itemRow.appendChild(equipLabel);


                const removeBtn = document.createElement('button');
                removeBtn.className = 'action-icon-btn';
                removeBtn.title = `Remove ${item.name}`;
                removeBtn.style.cssText = `width: 22px; height: 22px; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; background: hsla(215, 5%, 100%, 0.05); border: 1px solid hsla(215, 5%, 100%, 0.08); color: var(--text-muted); cursor: pointer; padding: 0; transition: all 0.15s ease;`;
                removeBtn.innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                `;
                removeBtn.onmouseover = () => {
                    removeBtn.style.color = 'var(--text-bright)';
                    removeBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.25)';
                    removeBtn.style.background = 'hsla(215, 5%, 100%, 0.12)';
                };
                removeBtn.onmouseout = () => {
                    removeBtn.style.color = 'var(--text-muted)';
                    removeBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.08)';
                    removeBtn.style.background = 'hsla(215, 5%, 100%, 0.05)';
                };
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    removeItemFromInventory(item.name);
                };
                itemRow.appendChild(removeBtn);

                invContainer.appendChild(itemRow);
            });
        }
    }

    // Spells
    const spellsContainer = document.getElementById('modal-char-spells');
    if (spellsContainer) {
        spellsContainer.innerHTML = '';
        const spells = char.spells || [];
        const spellCountEl = document.getElementById('inventory-spell-count');
        if (spellCountEl) spellCountEl.textContent = `${spells.length} ${spells.length === 1 ? 'spell' : 'spells'}`;
        if (spells.length === 0) {
            spellsContainer.innerHTML = '<span style="font-size: 0.8rem; color: var(--text-muted);">None known</span>';
        } else {
            spells.forEach(spell => {
                const badge = document.createElement('span');
                badge.style.cssText = 'font-size: 0.8rem; padding: 4px 6px 4px 10px; border-radius: 8px; background: hsla(218, 90%, 60%, 0.1); color: hsl(218, 90%, 60%); border: 1px solid hsla(218, 90%, 60%, 0.25); display: inline-flex; align-items: center; gap: 6px;';
                
                const spellText = document.createElement('span');
                spellText.textContent = `${spell.name} (${spell.school || 'Magic'}) • ${spell.mp_cost || spell.sp_cost || 4} MP`;
                badge.appendChild(spellText);

                const removeBtn = document.createElement('button');
                removeBtn.className = 'action-icon-btn';
                removeBtn.title = `Forget ${spell.name}`;
                removeBtn.style.cssText = `width: 22px; height: 22px; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; background: hsla(215, 5%, 100%, 0.05); border: 1px solid hsla(215, 5%, 100%, 0.08); color: var(--text-muted); cursor: pointer; padding: 0; transition: all 0.15s ease;`;
                removeBtn.innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                `;
                removeBtn.onmouseover = () => {
                    removeBtn.style.color = 'var(--text-bright)';
                    removeBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.25)';
                    removeBtn.style.background = 'hsla(215, 5%, 100%, 0.12)';
                };
                removeBtn.onmouseout = () => {
                    removeBtn.style.color = 'var(--text-muted)';
                    removeBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.08)';
                    removeBtn.style.background = 'hsla(215, 5%, 100%, 0.05)';
                };
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    removeSpellFromCharacter(spell.name);
                };
                badge.appendChild(removeBtn);
                spellsContainer.appendChild(badge);
            });
        }
    }

    // Effects & Conditions
    const effContainer = document.getElementById('modal-char-effects');
    if (effContainer) {
        const effects = char.active_effects || [];
        const conds = char.conditions || [];
        if (effects.length === 0 && conds.length === 0) {
            effContainer.textContent = 'None active';
        } else {
            const list = [...conds, ...effects.map(e => `${e.name} (${e.duration_turns}t)`)];
            effContainer.textContent = list.join(', ');
        }
    }
}

function toggleCharacterEditForm(forceState) {
    const panel = document.getElementById('char-edit-panel');
    if (!panel) return;
    if (forceState !== undefined) {
        panel.style.display = forceState ? 'block' : 'none';
    } else {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
    if (panel.style.display === 'block' && currentCharacterData && currentCharacterData.character) {
        const char = currentCharacterData.character;
        const nameInput = document.getElementById('edit-char-name');
        if (nameInput) nameInput.value = char.name || 'Eternal Champion';
        const genderSelect = document.getElementById('edit-char-gender');
        if (genderSelect) genderSelect.value = char.gender || 'Male';
        const raceSelect = document.getElementById('edit-char-race');
        if (raceSelect && char.race) raceSelect.value = char.race;
        const classSelect = document.getElementById('edit-char-class');
        if (classSelect && char.class) classSelect.value = char.class;
    }
}

async function saveCharacterCustomization() {
    const name = document.getElementById('edit-char-name')?.value || 'Eternal Champion';
    const gender = document.getElementById('edit-char-gender')?.value || 'Male';
    const race = document.getElementById('edit-char-race')?.value || 'Nord';
    const characterClass = document.getElementById('edit-char-class')?.value || 'Mage';

    try {
        const res = await fetch('/api/character/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                gender: gender,
                race: race,
                class: characterClass
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        toggleCharacterEditForm(false);
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error saving character profile:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Update Failed', e.message);
        }
    }
}

async function toggleItemEquip(itemName, currentEquipped) {
    try {
        const res = await fetch('/api/character/equip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name: itemName, equip: !currentEquipped, session_id: sessionId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error toggling equip state:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Equip Error', e.message);
        }
    }
}

async function removeItemFromInventory(itemName) {
    await executeRemoveItem(itemName);
}

async function dropItemFromInventory(itemName) {
    await executeRemoveItem(itemName);
}

async function executeRemoveItem(itemName) {
    try {
        const res = await fetch('/api/character/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name: itemName, quantity: 1, session_id: sessionId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error removing item:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Removal Error', e.message);
        }
    }
}

async function removeSpellFromCharacter(spellName) {
    try {
        const res = await fetch('/api/character/spell/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spell_name: spellName, session_id: sessionId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error removing spell:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Spell Removal Error', e.message);
        }
    }
}

async function modifyCharacterGold(amount, action = 'remove') {
    try {
        const res = await fetch('/api/character/gold/modify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: amount, action: action, session_id: sessionId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error modifying gold:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Gold Modification Error', e.message);
        }
    }
}

function openGoldEditModal() {
    let modal = document.getElementById('gold-edit-modal');
    const currentGold = currentCharacterData && currentCharacterData.character ? (currentCharacterData.character.gold || 0) : 0;
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'gold-edit-modal';
        modal.className = 'modal';
        modal.onclick = closeGoldEditModal;
        
        modal.innerHTML = `
            <div class="modal-card" style="max-width: 260px; width: 90%; text-align: left; align-items: stretch; padding: 18px;" onclick="event.stopPropagation()">
                <form onsubmit="event.preventDefault(); submitGoldEditModal();" style="display: flex; flex-direction: column; gap: 14px; margin: 0;">
                    <input type="number" id="gold-modal-input" min="0" style="width: 100%; box-sizing: border-box; background: rgba(0,0,0,0.4); border: 1px solid hsla(215, 5%, 100%, 0.15); border-radius: 8px; padding: 10px 12px; color: var(--text-bright); font-size: 1rem; outline: none; box-shadow: none;" onfocus="this.style.borderColor='hsla(215, 5%, 100%, 0.3)'; this.style.boxShadow='none';" />

                    <div style="display: flex; justify-content: flex-end; gap: 8px;">
                        <button type="button" onclick="closeGoldEditModal()" class="onboarding-btn" style="padding: 7px 14px; font-size: 0.8rem; background: hsla(215, 5%, 100%, 0.05); border: 1px solid hsla(215, 5%, 100%, 0.1); color: var(--text-muted);">
                            Cancel
                        </button>
                        <button type="submit" class="onboarding-btn" style="padding: 7px 18px; font-size: 0.8rem;">
                            Save
                        </button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    const inputEl = document.getElementById('gold-modal-input');
    if (inputEl) inputEl.value = currentGold;

    modal.style.display = 'flex';
    
    if (inputEl) {
        setTimeout(() => {
            inputEl.focus();
            inputEl.select();
        }, 50);
    }
}

function closeGoldEditModal() {
    const modal = document.getElementById('gold-edit-modal');
    if (modal) modal.style.display = 'none';
}

async function submitGoldEditModal() {
    const inputEl = document.getElementById('gold-modal-input');
    if (!inputEl) return;
    const val = parseInt(inputEl.value, 10);
    if (isNaN(val) || val < 0) return;
    closeGoldEditModal();
    await modifyCharacterGold(val, 'set');
}

function promptModifyGold() {
    openGoldEditModal();
}

function openNewItemModal() {
    const modal = document.getElementById('new-item-modal');
    if (!modal) return;
    const inputEl = document.getElementById('new-item-input');
    const statusEl = document.getElementById('new-item-status');
    const submitBtn = document.getElementById('new-item-submit-btn');
    if (inputEl) inputEl.value = '';
    if (statusEl) statusEl.style.display = 'none';
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create';
    }
    modal.style.display = 'flex';
    if (inputEl) {
        setTimeout(() => {
            inputEl.focus();
        }, 50);
    }
}

function closeNewItemModal() {
    const modal = document.getElementById('new-item-modal');
    if (modal) modal.style.display = 'none';
}

async function submitNewItemModal() {
    const inputEl = document.getElementById('new-item-input');
    const statusEl = document.getElementById('new-item-status');
    const submitBtn = document.getElementById('new-item-submit-btn');
    if (!inputEl) return;
    const desc = inputEl.value.trim();
    if (!desc) {
        inputEl.focus();
        return;
    }

    if (statusEl) statusEl.style.display = 'flex';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Forging item...';
    }

    try {
        const activeModel = (typeof selectedModel !== 'undefined' && selectedModel) ? selectedModel : (document.getElementById('model-select')?.value || '');
        const res = await fetch('/api/character/item/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: desc,
                session_id: sessionId,
                model: activeModel
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        closeNewItemModal();
        await fetchCharacterStatus();
    } catch (e) {
        console.error('Error creating item:', e);
        if (typeof showCustomAlert === 'function') {
            showCustomAlert('Item Creation Error', e.message);
        }
    } finally {
        if (statusEl) statusEl.style.display = 'none';
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create';
        }
    }
}


// --- updateInputGlow ---
function updateInputGlow() {
    const wrapper = document.querySelector('.input-wrapper');
    if (!userInput || !wrapper) return;
    const text = userInput.value.trim();
    if (text.length > 0 && !isGenerating) {
        wrapper.classList.add('has-unsent-text');
    } else {
        wrapper.classList.remove('has-unsent-text');
    }
}

// --- getLogIconSvg ---
function getLogIconSvg(name) {
    const svgs = {
        timer: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
        file: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`,
        webpage: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
        folder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`,
        search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
        edit: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>`,
        command: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>`,
        gear: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06-.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`
    };
    return svgs[name] || svgs.command;
}

// --- getProfileUrl ---
function getProfileUrl() {
    return `/profile.png?t=${profileCacheBuster}`;
}

// Helper to update profile/list avatars, automatically restoring from fallback DIVs to IMGs
function updateAvatarElement(el, newSrc) {
    if (el.classList.contains('avatar-fallback') || el.tagName === 'DIV') {
        const img = document.createElement('img');
        img.className = el.className.replace('avatar-fallback', '').trim();
        img.src = newSrc;
        img.alt = el.getAttribute('alt') || 'Program';
        
        // Copy all attributes back
        for (let attr of el.attributes) {
            if (attr.name !== 'class' && attr.name !== 'style' && attr.name !== 'src') {
                img.setAttribute(attr.name, attr.value);
            }
        }
        
        img.style.cssText = el.style.cssText;
        img.style.display = 'block';
        
        if (el.onclick) {
            img.onclick = el.onclick;
        } else if (el.classList.contains('program-avatar')) {
            img.onclick = () => expandImage(newSrc);
        }
        
        el.replaceWith(img);
    } else {
        el.src = newSrc;
        if (el.classList.contains('program-avatar')) {
            el.onclick = () => expandImage(newSrc);
        }
    }
}

// --- updateProfileImages ---
function updateProfileImages() {
    const url = getProfileUrl();
    document.querySelectorAll('.program-avatar').forEach(img => {
        updateAvatarElement(img, url);
    });
}

// --- applyTheme ---
function applyTheme(programId, theme) {
    document.body.className = programId;
    const root = document.documentElement;
    if (theme) {
        if (theme.main_color) root.style.setProperty('--main-color', theme.main_color);
        if (theme.accent_color_a) root.style.setProperty('--accent-color-a', theme.accent_color_a);
        if (theme.accent_color_b) root.style.setProperty('--accent-color-b', theme.accent_color_b);
        if (theme.primary_accent) root.style.setProperty('--primary-accent', theme.primary_accent);
        if (theme.primary_glow) root.style.setProperty('--primary-glow', theme.primary_glow);
        if (theme.program_bubble) root.style.setProperty('--program-bubble', theme.program_bubble);
        if (theme.send_btn_hover) root.style.setProperty('--send-btn-hover', theme.send_btn_hover);
        if (theme.accent_green) {
            root.style.setProperty('--accent-green', theme.accent_green);
        }
        if (theme.quote_blue) root.style.setProperty('--quote-blue', theme.quote_blue);
        if (theme.primary_btn_text) root.style.setProperty('--primary-btn-text', theme.primary_btn_text);
    } else {
        // Default theme values
        root.style.setProperty('--main-color', '#8b5cf6');
        root.style.setProperty('--accent-color-a', '#b19cd9');
        root.style.setProperty('--accent-color-b', '#79aeff');
        root.style.setProperty('--primary-accent', '#8b5cf6');
        root.style.setProperty('--primary-glow', 'rgba(139, 92, 246, 0.08)');
        root.style.setProperty('--program-bubble', 'rgba(24, 22, 28, 0.85)');
        root.style.setProperty('--send-btn-hover', 'rgba(45, 38, 56, 0.75)');
        root.style.setProperty('--accent-green', '#b19cd9');
        root.style.setProperty('--quote-blue', '#79aeff');
        root.style.setProperty('--primary-btn-text', 'var(--text-bright)');
    }
}

// --- updateConnectionStatus ---
function updateConnectionStatus(status) {
    if (!status) return;
    connectionStatus = status;
    
    const headerStatusText = document.getElementById('header-status-text');
    const headerHeart = document.getElementById('header-heart-pulse');
    
    const geminiBadges = [
        document.getElementById('onboarding-gemini-status'),
        document.getElementById('modal-gemini-status')
    ];
    const localLLMBadges = [
        document.getElementById('onboarding-local-status'),
        document.getElementById('modal-local-status')
    ];
    
    // Update Gemini badges
    geminiBadges.forEach(badge => {
        if (!badge) return;
        if (status.remote_configured ) {
            badge.textContent = "Configured";
            badge.className = "status-badge status-configured";
        } else {
            badge.textContent = "Unconfigured";
            badge.className = "status-badge status-unconfigured";
        }
    });
    
    // Update Local LLM badges
    localLLMBadges.forEach(badge => {
        if (!badge) return;
        if (status.local_online === true || status.local_online === 'online') {
            badge.textContent = "Online";
            badge.className = "status-badge status-online";
        } else if (status.local_online === 'starting') {
            badge.textContent = "Starting...";
            badge.className = "status-badge status-starting";
        } else if (status.local_online === 'stopping') {
            badge.textContent = "Stopping...";
            badge.className = "status-badge status-starting";
        } else {
            badge.textContent = "Offline";
            badge.className = "status-badge status-offline";
        }
    });
    
    // Update Header status indicator
    if (headerStatusText) {
        if (status.remote_configured  || status.local_online) {
            headerStatusText.textContent = "";
        } else {
            headerStatusText.textContent = "Disconnected";
        }
    }

}

// --- updateConnectionModalStatus ---
function updateConnectionModalStatus() {
    const modalApiKey = document.getElementById('modal-api-key');
    const modalProjectId = document.getElementById('modal-project-id');
    const modalGeminiModel = document.getElementById('modal-gemini-model');
    
    // Dynamically set dynamism slider
    const tempVal = connectionStatus.temperature !== undefined ? connectionStatus.temperature : 0.95;
    const dynamismSlider = document.getElementById('dynamism-slider');
    const dynamismCurrentVal = document.getElementById('dynamism-current-val');
    if (dynamismSlider) {
        dynamismSlider.value = tempVal;
        if (dynamismCurrentVal) dynamismCurrentVal.textContent = parseFloat(tempVal).toFixed(2);
    }
    
    if (connectionStatus.remote_configured ) {
        if (modalApiKey && !modalApiKey.value) modalApiKey.placeholder = "•••••••••••••••• (Configured)";
        if (modalProjectId && !modalProjectId.value && connectionStatus.remote_url) {
            modalProjectId.value = connectionStatus.remote_url;
        }
    }
    
    if (modalGeminiModel && !modalGeminiModel.value && connectionStatus.remote_model) {
        modalGeminiModel.value = connectionStatus.remote_model;
    }
    
    const envPathEl = document.querySelector('.env-path');
    if (envPathEl && connectionStatus.env_path) {
        envPathEl.textContent = connectionStatus.env_path;
    }
    
    updateConnectionStatus(connectionStatus);

    // Update the Local box panel states inside settings modal
    const localBox = document.getElementById('modal-local-box-container');
    if (localBox) {
        const localDesc = document.getElementById('modal-local-desc');
        const startBtn = document.getElementById('modal-local-start-btn');
        const stopBtn = document.getElementById('modal-local-stop-btn');
        
        if (connectionStatus.local_online === 'starting' || _localStarting) {
            if (localDesc) localDesc.textContent = "Local LLM engine is currently starting up in the background. Please wait...";
            if (startBtn) {
                startBtn.style.display = 'block';
                startBtn.disabled = true;
                startBtn.textContent = "Starting...";
            }
            if (stopBtn) stopBtn.style.display = 'none';
        } else if (_localStopping) {
            if (localDesc) localDesc.textContent = "Local LLM engine is stopping. Please wait...";
            if (startBtn) {
                startBtn.style.display = 'block';
                startBtn.disabled = true;
                startBtn.textContent = "Stopping...";
            }
            if (stopBtn) stopBtn.style.display = 'none';
        } else if (!connectionStatus.local_online) {
            if (localDesc) localDesc.textContent = "Local LLM engine is offline. Start the server or search Hugging Face below to download a GGUF model.";
            if (startBtn) {
                startBtn.style.display = 'block';
                startBtn.disabled = false;
                startBtn.textContent = "Start Server";
            }
            if (stopBtn) stopBtn.style.display = 'none';
        } else {
            if (localDesc) localDesc.textContent = "Local LLM server is running. Select active models via the header dropdown.";
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) {
                stopBtn.style.display = 'block';
                stopBtn.disabled = false;
                stopBtn.textContent = "Stop Server";
            }
        }
        fetchAndRenderLocalModels();
    }
}

// --- updateComfyModalStatus ---
// skipFetch: when true, use in-memory comfyStatus (already populated by SSE or button handlers)
async function updateComfyModalStatus(skipFetch = false) {
    // Debounce: coalesce rapid consecutive calls into a single update
    if (_comfyUpdateRunning) {
        if (!_comfyUpdateTimer) {
            _comfyUpdateTimer = setTimeout(() => {
                _comfyUpdateTimer = null;
                updateComfyModalStatus(skipFetch);
            }, 200);
        }
        return;
    }
    _comfyUpdateRunning = true;

    try {
        if (!skipFetch) {
            const res = await fetch('/api/comfy/status');
            comfyStatus = await res.json();
        }
        
        const comfyBox = document.getElementById('modal-comfy-box-container');
        if (comfyBox) {
            const statusBadge = document.getElementById('modal-comfy-status');
            if (statusBadge) {
                if (comfyStatus.running === true || comfyStatus.running === 'online') {
                    statusBadge.textContent = "Running";
                    statusBadge.className = "status-badge status-online";
                } else if (comfyStatus.running === 'starting') {
                    statusBadge.textContent = "Starting...";
                    statusBadge.className = "status-badge status-starting";
                } else if (comfyStatus.running === 'stopping') {
                    statusBadge.textContent = "Stopping...";
                    statusBadge.className = "status-badge status-starting";
                } else if (comfyStatus.installed) {
                    statusBadge.textContent = "Offline";
                    statusBadge.className = "status-badge status-offline";
                } else {
                    statusBadge.textContent = "Uninstalled";
                    statusBadge.className = "status-badge status-offline";
                }
            }
            
            if (!comfyStatus.installed) {
                _comfyCheckpointsInitialized = false;
                if (comfyStatus.resolution_status && comfyStatus.resolution_status.status === "resolving") {
                    let percentWidth = "0%";
                    const text = comfyStatus.resolution_status.progress;
                    const match = text.match(/(\d+)%/);
                    if (match) {
                        percentWidth = match[1] + '%';
                    }
                    
                    comfyBox.innerHTML = `
                        <div class="option-header">
                            <h4 style="margin: 0; font-size: 1.05rem; font-weight: 600;">ComfyUI (Portraits)</h4>
                            <span class="status-badge status-offline">Installing...</span>
                        </div>
                        <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">ComfyUI is installing in the background.</p>
                        <div id="comfy-install-progress" style="margin-top: 10px; font-size: 0.85rem; color: var(--text-main);">
                            <div style="font-weight: 500; margin-bottom: 5px;">Status: INSTALLING</div>
                            <div style="font-style: italic; margin-bottom: 8px;" id="comfy-install-progress-text">${comfyStatus.resolution_status.progress}</div>
                            <div style="background: hsla(215, 5%, 100%, 0.05); border-radius: 4px; height: 6px; width: 100%; overflow: hidden;">
                                <div id="comfy-install-progress-bar" style="background: var(--primary-accent); height: 100%; width: ${percentWidth};"></div>
                            </div>
                        </div>
                    `;
                    setTimeout(() => updateComfyModalStatus(false), 2000);
                } else {
                    comfyBox.innerHTML = `
                        <div class="option-header">
                            <h4 style="margin: 0; font-size: 1.05rem; font-weight: 600;">ComfyUI (Portraits)</h4>
                            <span id="modal-comfy-status" class="status-badge status-offline">Uninstalled</span>
                        </div>
                        <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 15px 0;">ComfyUI is not detected in your workspace or destination directory.</p>
                        <button onclick="installComfyUI(this)" class="onboarding-btn connect-cloud-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 10px;">Auto-Install ComfyUI</button>
                    `;
                }
            } else {
                // Check if checkpoint manager is already rendered to avoid resetting user inputs/lists
                const managerExists = document.getElementById('comfy-checkpoint-manager');
                if (managerExists) {
                    // Just update status and button controls dynamically
                    const badge = document.getElementById('modal-comfy-status');
                    if (badge) {
                        if (comfyStatus.running === true || comfyStatus.running === 'online') {
                            badge.textContent = "Running";
                            badge.className = "status-badge status-online";
                        } else if (comfyStatus.running === 'starting') {
                            badge.textContent = "Starting...";
                            badge.className = "status-badge status-starting";
                        } else if (comfyStatus.running === 'stopping') {
                            badge.textContent = "Stopping...";
                            badge.className = "status-badge status-starting";
                        } else {
                            badge.textContent = "Offline";
                            badge.className = "status-badge status-offline";
                        }
                    }
                    
                    // Defer controls update when user is interacting with the search input
                    const activeEl = document.activeElement;
                    const isUserTyping = activeEl && (activeEl.id === 'comfy-hf-search-input');
                    
                    // Update the controls container (Start/Stop button etc.) only when not mid-operation
                    const controls = document.getElementById('comfy-engine-controls');
                    if (controls && !_comfyResolving) {
                        const isRunning = comfyStatus.running === true || comfyStatus.running === 'online';
                        const isStarting = comfyStatus.running === 'starting' || _comfyStarting;
                        const isStopping = comfyStatus.running === 'stopping' || _comfyStopping;
                        
                        if (isRunning) {
                            controls.innerHTML = `
                                <button onclick="stopComfyUI(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px;">Stop ComfyUI</button>
                                <button onclick="resolveWorkflowDependencies(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 8px; margin-bottom: 5px;">Resolve Workflow Dependencies</button>
                            `;
                        } else if (isStarting) {
                            controls.innerHTML = `
                                <button disabled class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px; opacity: 0.7;">Starting ComfyUI...</button>
                            `;
                        } else if (isStopping) {
                            controls.innerHTML = `
                                <button disabled class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px; opacity: 0.7;">Stopping ComfyUI...</button>
                            `;
                        } else {
                            controls.innerHTML = `
                                <button onclick="startComfyUI(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px;">Start ComfyUI</button>
                            `;
                        }
                    }
                    
                    // Update progress bar if resolving
                    const progressDiv = document.getElementById('comfy-resolution-progress');
                    if (progressDiv && comfyStatus.resolution_status) {
                        const r = comfyStatus.resolution_status;
                        if (r.status !== "idle") {
                            let errorHtml = "";
                            if (r.errors && r.errors.length > 0) {
                                errorHtml = `<div style="color: var(--danger-bright); margin-top: 4px;">Errors: ${r.errors.join(", ")}</div>`;
                            }
                            progressDiv.innerHTML = `
                                <div style="font-weight: 500; color: var(--text-main); margin-top: 8px; margin-bottom: 3px;">Status: ${r.status.toUpperCase()}</div>
                                <div style="margin-top: 2px; font-style: italic;">${r.progress}</div>
                                ${errorHtml}
                            `;
                            if (r.status === "resolving") {
                                setTimeout(() => updateComfyModalStatus(false), 2000);
                            }
                        } else {
                            progressDiv.innerHTML = '';
                        }
                    }
                } else {
                    // Render full ComfyUI installed view (including Checkpoint Manager)
                    comfyBox.innerHTML = `
                         <div class="option-header">
                             <h4 style="margin: 0; font-size: 1.05rem; font-weight: 600;">ComfyUI (Portraits)</h4>
                             <span id="modal-comfy-status" class="status-badge ${comfyStatus.running === 'starting' || comfyStatus.running === 'stopping' ? 'status-starting' : (comfyStatus.running ? 'status-online' : 'status-offline')}">
                                 ${comfyStatus.running === 'starting' ? 'Starting...' : (comfyStatus.running === 'stopping' ? 'Stopping...' : (comfyStatus.running ? 'Running' : 'Offline'))}
                             </span>
                         </div>
                         <p class="option-desc" style="font-size: 0.8rem; margin: 8px 0 10px 0;">Generate program portraits locally using ComfyUI.</p>
                         
                         <div id="comfy-engine-controls">
                             ${comfyStatus.running === true || comfyStatus.running === 'online' ? `
                                 <button onclick="stopComfyUI(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px;">Stop ComfyUI</button>
                                 <button onclick="resolveWorkflowDependencies(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 8px; margin-bottom: 5px;">Resolve Workflow Dependencies</button>
                             ` : (comfyStatus.running === 'starting' ? `
                                 <button disabled class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px; opacity: 0.7;">Starting ComfyUI...</button>
                             ` : (comfyStatus.running === 'stopping' ? `
                                 <button disabled class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px; opacity: 0.7;">Stopping ComfyUI...</button>
                             ` : `
                                 <button onclick="startComfyUI(this)" class="onboarding-btn" style="width: 100%; font-size: 0.85rem; padding: 10px; margin-top: 5px;">Start ComfyUI</button>
                             `))}
                         </div>
                        <div id="comfy-resolution-progress" style="font-size: 0.72rem; color: var(--text-muted); line-height: 1.3;"></div>
                        
                        <div id="comfy-checkpoint-manager" style="border-top: 1px solid var(--border-color); padding-top: 15px; margin-top: 15px; text-align: left;">
                            <div style="margin-bottom: 15px;">
                                <label style="font-size: 0.72rem; color: var(--text-muted); font-weight: 600; display: block; margin-bottom: 6px;">Active Checkpoint Model:</label>
                                <select id="comfy-checkpoint-select" onchange="changeComfyCheckpoint()" class="onboarding-input glass-select" style="width: 100%; font-size: 0.8rem; background: rgba(0,0,0,0.25); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 6px; outline: none; height: 32px; box-sizing: border-box;">
                                    <option>Loading checkpoints...</option>
                                </select>
                                <button onclick="fetchComfyCheckpoints()" class="onboarding-btn" style="width: 100%; margin-top: 8px; font-size: 0.8rem; padding: 6px; height: 32px;">Refresh Checkpoints</button>
                            </div>
                            
                            <div style="margin-bottom: 10px;">
                                <label style="font-size: 0.72rem; color: var(--text-muted); font-weight: 600; display: block; margin-bottom: 6px;">Search Hugging Face (Checkpoints):</label>
                                <input type="text" id="comfy-hf-search-input" placeholder="e.g. sd_xl, pony, custom_art" class="onboarding-input" style="width: 100%; font-size: 0.8rem; padding: 6px 10px; height: 32px; box-sizing: border-box;" onkeydown="if(event.key==='Enter') searchComfyHFCheckpoints()">
                                <button onclick="searchComfyHFCheckpoints()" class="onboarding-btn" style="width: 100%; margin-top: 8px; font-size: 0.8rem; padding: 6px; height: 32px;">Search Checkpoints</button>
                                <div id="comfy-hf-search-results" style="margin-top: 10px; max-height: 140px; overflow-y: auto; font-size: 0.75rem; display: flex; flex-direction: column; gap: 6px; padding-right: 4px;"></div>
                            </div>
                            
                            <div id="comfy-checkpoint-downloads-container" style="display: none; font-size: 0.72rem; color: var(--text-muted); border-top: 1px solid hsla(215, 5%, 100%, 0.05); padding-top: 10px; margin-top: 10px;">
                                <div style="font-weight: 600; color: var(--text-color); margin-bottom: 5px;">Active Downloads:</div>
                                <div id="comfy-checkpoint-downloads-list" style="display: flex; flex-direction: column; gap: 6px;"></div>
                            </div>
                        </div>
                    `;
                    
                    // Trigger initial checkpoints loading only once per panel lifecycle
                    if (!_comfyCheckpointsInitialized) {
                        _comfyCheckpointsInitialized = true;
                        fetchComfyCheckpoints();
                        pollComfyCheckpointDownloads();
                    }
                }
            }
        }
    } catch (e) {
        console.error("Error fetching ComfyUI status:", e);
    } finally {
        _comfyUpdateRunning = false;

    }
}



// --- openConnectionModal ---
function openConnectionModal() {
    document.getElementById('connection-modal').style.display = 'flex';
    updateConnectionModalStatus();
    verifyConnections(true);
    updateComfyModalStatus();
}

// --- closeConnectionModal ---
function closeConnectionModal() {
    document.getElementById('connection-modal').style.display = 'none';
    _comfyCheckpointsInitialized = false;
    if (_comfyUpdateTimer) {
        clearTimeout(_comfyUpdateTimer);
        _comfyUpdateTimer = null;
    }
}

// --- openUserProfileModal ---
function openUserProfileModal() {
    openAssistantModal('program');
}

// --- closeUserProfileModal ---
function closeUserProfileModal() {
    closeAssistantModal();
}

// --- changeModel ---
async function changeModel() {
    const select = document.getElementById('model-select');
    if (select) {
        const val = select.value;
        selectedModel = val;
        localStorage.setItem('program_selected_model', selectedModel);
    }
}

// --- showCustomAlert ---
function showCustomAlert(title, message, callback = null) {
    const modalDeco = document.querySelector('#custom-dialog-modal .modal-card');
    if (modalDeco) modalDeco.style.maxWidth = '400px';

    document.getElementById('custom-dialog-title').innerHTML = title;
    document.getElementById('custom-dialog-message').innerHTML = message;
    
    const buttonsContainer = document.getElementById('custom-dialog-buttons');
    buttonsContainer.innerHTML = `
        <button onclick="closeCustomDialog(true)" class="edit-btn edit-save-btn" style="min-width: 100px;">
            OK
        </button>
    `;
    
    customDialogCallback = callback;
    customDialogCancelCallback = null;
    document.getElementById('custom-dialog-modal').style.display = 'flex';
}

// --- showCustomConfirm ---
function showCustomConfirm(title, message, onConfirm, onCancel = null) {
    const modalDeco = document.querySelector('#custom-dialog-modal .modal-card');
    if (modalDeco) modalDeco.style.maxWidth = '400px';

    document.getElementById('custom-dialog-title').innerHTML = title;
    document.getElementById('custom-dialog-message').innerHTML = message;
    
    const buttonsContainer = document.getElementById('custom-dialog-buttons');
    buttonsContainer.innerHTML = `
        <button onclick="closeCustomDialog(false)" class="edit-btn edit-cancel-btn" style="min-width: 100px;">
            Cancel
        </button>
        <button onclick="closeCustomDialog(true)" class="edit-btn edit-save-btn" style="min-width: 100px;">
            Confirm
        </button>
    `;
    
    customDialogCallback = onConfirm;
    customDialogCancelCallback = onCancel;
    document.getElementById('custom-dialog-modal').style.display = 'flex';
}

// --- closeCustomDialog ---
function closeCustomDialog(approved) {
    document.getElementById('custom-dialog-modal').style.display = 'none';
    if (approved && customDialogCallback) {
        customDialogCallback();
    } else if (!approved && customDialogCancelCallback) {
        customDialogCancelCallback();
    }
}

// --- showCustomPrompt ---
function showCustomPrompt(title, message, defaultValue, onConfirm, onCancel = null) {
    const modalDeco = document.querySelector('#custom-dialog-modal .modal-card');
    if (modalDeco) modalDeco.style.maxWidth = '400px';

    document.getElementById('custom-dialog-title').innerHTML = title;
    document.getElementById('custom-dialog-message').innerHTML = `
        <p style="margin-top: 0; margin-bottom: 10px;">${message}</p>
        <input type="text" id="custom-dialog-input" value="${defaultValue}" class="onboarding-input" style="font-size: 0.9rem; margin-bottom: 10px;">
    `;
    
    const buttonsContainer = document.getElementById('custom-dialog-buttons');
    buttonsContainer.innerHTML = `
        <button onclick="closeCustomDialog(false)" class="edit-btn edit-cancel-btn" style="min-width: 100px;">
            Cancel
        </button>
        <button id="custom-dialog-submit-btn" class="edit-btn edit-save-btn" style="min-width: 100px;">
            Confirm
        </button>
    `;
    
    const submitBtn = document.getElementById('custom-dialog-submit-btn');
    const submitAction = () => {
        const val = document.getElementById('custom-dialog-input').value;
        document.getElementById('custom-dialog-modal').style.display = 'none';
        if (onConfirm) onConfirm(val);
    };
    submitBtn.onclick = submitAction;
    
    const inputField = document.getElementById('custom-dialog-input');
    inputField.onkeydown = (e) => {
        if (e.key === 'Enter') {
            submitAction();
        }
    };
    
    customDialogCallback = null;
    customDialogCancelCallback = onCancel;
    
    document.getElementById('custom-dialog-modal').style.display = 'flex';
    setTimeout(() => inputField.focus(), 50);
}

// --- showCustomTextareaPrompt ---
function showCustomTextareaPrompt(title, message, defaultValue, onConfirm, onCancel = null) {
    const modalDeco = document.querySelector('#custom-dialog-modal .modal-card');
    if (modalDeco) modalDeco.style.maxWidth = '600px';

    document.getElementById('custom-dialog-title').innerHTML = title;
    document.getElementById('custom-dialog-message').innerHTML = `
        <p style="margin-top: 0; margin-bottom: 10px;">${message}</p>
        <textarea id="custom-dialog-input" class="onboarding-input" style="height: 160px; font-size: 0.9rem; margin-bottom: 10px; resize: vertical; font-family: inherit; line-height: 1.5;"></textarea>
    `;
    
    const inputField = document.getElementById('custom-dialog-input');
    if (inputField) inputField.value = defaultValue || "";
    
    const buttonsContainer = document.getElementById('custom-dialog-buttons');
    buttonsContainer.innerHTML = `
        <button onclick="closeCustomDialog(false)" class="edit-btn edit-cancel-btn" style="min-width: 100px;">
            Cancel
        </button>
        <button id="custom-dialog-submit-btn" class="edit-btn edit-save-btn" style="min-width: 100px;">
            Confirm
        </button>
    `;
    
    const submitBtn = document.getElementById('custom-dialog-submit-btn');
    const submitAction = () => {
        const val = document.getElementById('custom-dialog-input').value;
        document.getElementById('custom-dialog-modal').style.display = 'none';
        if (onConfirm) onConfirm(val);
    };
    submitBtn.onclick = submitAction;
    
    if (inputField) {
        inputField.onkeydown = (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                submitAction();
            }
        };
    }
    
    customDialogCallback = null;
    customDialogCancelCallback = onCancel;
    
    document.getElementById('custom-dialog-modal').style.display = 'flex';
    setTimeout(() => { if (inputField) inputField.focus(); }, 50);
}

/* ==========================================================================
   VI. 5. USER PROFILE MANAGEMENT
   ========================================================================== */

let selectedEditingProfileId = "";

// --- loadUserProfiles ---
async function loadUserProfiles() {
    try {
        const response = await fetch('/api/user_profiles');
        const data = await response.json();
        if (data.error) {
            console.error("Failed to load user profiles:", data.error);
            return;
        }
        userProfiles = data.profiles || [];
        activeUserProfile = data.active || "";
        
        if (!selectedEditingProfileId || !userProfiles.some(p => p.id === selectedEditingProfileId)) {
            selectedEditingProfileId = activeUserProfile;
        }
        
        renderUserProfilesList();
    } catch (e) {
        console.error("Error fetching user profiles:", e);
    }
}

// --- renderUserProfilesList ---
function renderUserProfilesList() {
    const container = document.getElementById('user-profiles-list-container');
    if (!container) return;
    container.innerHTML = '';

    userProfiles.forEach(prof => {
        const isActive = prof.id === activeUserProfile;

        const card = document.createElement('div');
        card.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: ${isActive ? 'hsla(var(--gold-h), var(--gold-s), 45%, 0.12)' : 'hsla(215, 5%, 100%, 0.03)'};
            border: 1px solid ${isActive ? 'var(--primary-accent)' : 'var(--border-color)'};
            box-shadow: ${isActive ? '0 0 14px var(--primary-glow)' : 'none'};
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        `;

        card.onmouseover = () => {
            if (!isActive) {
                card.style.background = 'hsla(215, 5%, 100%, 0.07)';
                card.style.borderColor = 'hsla(215, 5%, 100%, 0.2)';
            }
        };
        card.onmouseout = () => {
            if (!isActive) {
                card.style.background = 'hsla(215, 5%, 100%, 0.03)';
                card.style.borderColor = 'var(--border-color)';
            }
        };
        card.onclick = () => {
            if (!isActive) {
                activateUserProfile(prof.id);
            }
        };

        // Left info area
        const leftArea = document.createElement('div');
        leftArea.style.cssText = 'display: flex; align-items: center; gap: 12px;';

        // User avatar icon container
        const avatarDiv = document.createElement('div');
        avatarDiv.style.cssText = `
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: ${isActive ? 'hsla(var(--gold-h), var(--gold-s), 45%, 0.2)' : 'hsla(215, 5%, 100%, 0.08)'};
            border: 2px solid ${isActive ? 'var(--primary-accent)' : 'var(--border-color)'};
            display: flex;
            align-items: center;
            justify-content: center;
            color: ${isActive ? 'var(--gold-bright)' : 'var(--text-main)'};
            flex-shrink: 0;
        `;
        avatarDiv.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
        `;
        leftArea.appendChild(avatarDiv);

        const info = document.createElement('div');
        info.style.cssText = 'display: flex; flex-direction: column; gap: 2px;';

        const nameDiv = document.createElement('div');
        nameDiv.style.cssText = 'font-size: 0.95rem; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 8px;';
        nameDiv.innerText = prof.character_name || prof.name || 'Eternal Champion';

        if (isActive) {
            const activeBadge = document.createElement('span');
            activeBadge.style.cssText = 'font-size: 0.65rem; padding: 2px 7px; border-radius: 10px; background: hsla(var(--gold-h), var(--gold-s), 45%, 0.25); color: var(--gold-bright); border: 1px solid var(--border-color); font-weight: 700; letter-spacing: 0.02em;';
            activeBadge.innerText = 'Active Save';
            nameDiv.appendChild(activeBadge);
        }

        info.appendChild(nameDiv);

        // Format slot display (e.g. "[Save1]" or "[Save2]")
        const slotMatch = prof.id.match(/_(\d+)$/);
        const slotLabel = slotMatch ? `Save${slotMatch[1]}` : 'Save1';

        const idDiv = document.createElement('div');
        idDiv.style.cssText = 'font-size: 0.78rem; color: var(--text-muted); font-weight: 500; margin-top: 2px;';
        idDiv.innerText = `Level ${prof.level || 1} ${prof.race || 'Nord'} ${prof.class || 'Mage'} [${slotLabel}]`;
        info.appendChild(idDiv);

        leftArea.appendChild(info);
        card.appendChild(leftArea);

        // Right side action area (matching program profile rows)
        const rightArea = document.createElement('div');
        rightArea.style.cssText = 'display: flex; align-items: center; gap: 6px; margin-left: auto;';

        // Add Edit Settings button on each save row
        const editBtn = document.createElement('button');
        editBtn.className = 'action-icon-btn';
        editBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
        `;
        editBtn.title = 'Edit Character / Save Info';
        editBtn.style.width = '26px';
        editBtn.style.height = '26px';
        editBtn.style.borderRadius = '6px';
        editBtn.style.flexShrink = '0';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            openUserProfileEditor(prof.id);
        };
        rightArea.appendChild(editBtn);

        // Add Delete button on save row
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'action-icon-btn';
        deleteBtn.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
        `;
        deleteBtn.title = 'Delete Save';
        deleteBtn.style.width = '26px';
        deleteBtn.style.height = '26px';
        deleteBtn.style.borderRadius = '6px';
        deleteBtn.style.flexShrink = '0';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteUserProfileById(prof.id);
        };
        rightArea.appendChild(deleteBtn);

        card.appendChild(rightArea);
        container.appendChild(card);
    });
}

// --- saveActiveGameSlot ---
async function saveActiveGameSlot() {
    try {
        const response = await fetch('/api/saves/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await response.json();
        if (data.status === 'success') {
            showCustomAlert("Save Game", `Game saved as ${data.save.id}!`);
            await loadUserProfiles();
            if (typeof fetchCharacterStatus === 'function') {
                fetchCharacterStatus();
            }
        } else {
            showCustomAlert("Save Error", data.error || "Failed to save game.");
        }
    } catch (err) {
        console.error("Error saving game:", err);
        showCustomAlert("Error", "Could not connect to the server to save game.");
    }
}

// --- openUserProfileEditor ---
function openUserProfileEditor(profileId) {
    selectedEditingProfileId = profileId;
    populateProfileEditor();
    
    const listView = document.getElementById('user-profiles-list-view');
    const editView = document.getElementById('user-profile-edit-view');
    if (listView) listView.style.display = 'none';
    if (editView) editView.style.display = 'block';
}

// --- closeUserProfileEditor ---
function closeUserProfileEditor() {
    const listView = document.getElementById('user-profiles-list-view');
    const editView = document.getElementById('user-profile-edit-view');
    if (listView) listView.style.display = 'block';
    if (editView) editView.style.display = 'none';
    renderUserProfilesList();
}

// --- populateProfileEditor ---
function populateProfileEditor() {
    const prof = userProfiles.find(p => p.id === selectedEditingProfileId);
    const nameInput = document.getElementById('user-profile-name-input');
    const contentTextarea = document.getElementById('user-profile-content');
    const activeBadge = document.getElementById('active-profile-badge');
    const statusText = document.getElementById('profile-status-text');
    const deleteBtn = document.getElementById('delete-profile-btn');

    if (!prof) return;

    if (nameInput) nameInput.value = prof.character_name || prof.name;
    if (contentTextarea) contentTextarea.value = prof.content;

    // Populate Character Trinity (Gender, Race, Class) from profile data
    const genderSelect = document.getElementById('user-profile-gender-select');
    if (genderSelect && prof.gender) genderSelect.value = prof.gender;
    const raceSelect = document.getElementById('user-profile-race-select');
    if (raceSelect && prof.race) raceSelect.value = prof.race;
    const classSelect = document.getElementById('user-profile-class-select');
    if (classSelect && prof.class) classSelect.value = prof.class;

    if (selectedEditingProfileId === activeUserProfile) {
        if (activeBadge) activeBadge.style.display = 'inline-block';
        if (statusText) statusText.textContent = "";
    } else {
        if (activeBadge) activeBadge.style.display = 'none';
        if (statusText) statusText.textContent = "(Not Active)";
    }

    if (deleteBtn) {
        deleteBtn.style.display = selectedEditingProfileId ? 'inline-block' : 'none';
    }
}

function onUserProfileFieldInput() {
    const statusText = document.getElementById('profile-status-text');
    if (statusText) statusText.textContent = "Unsaved Changes";
}

// --- activateUserProfile ---
async function activateUserProfile(profileId) {
    try {
        const res = await fetch('/api/user_profiles/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_id: profileId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        closeAssistantModal();
        window.location.reload();
    } catch (e) {
        showCustomAlert("Error", e.message || "Failed to activate profile.");
    }
}

// --- saveActiveUserProfile ---
async function saveActiveUserProfile() {
    const nameInput = document.getElementById('user-profile-name-input');
    const textarea = document.getElementById('user-profile-content');
    const saveBtn = document.getElementById('save-profile-btn');

    if (!selectedEditingProfileId || !nameInput || !textarea) return;

    let profileId = selectedEditingProfileId;
    const newName = nameInput.value.trim();
    let content = textarea.value;

    if (!newName) {
        showCustomAlert("Error", "Profile name cannot be empty.");
        return;
    }

    // Sync header title in markdown content
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";
    }

    try {
        const prof = userProfiles.find(p => p.id === profileId);

        // If the user changed the name, call rename API first
        if (prof && prof.character_name !== newName && prof.name !== newName) {
            const renameRes = await fetch('/api/user_profiles/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_profile_id: profileId, new_profile_name: newName })
            });
            const renameData = await renameRes.json();
            if (renameData.error) throw new Error(renameData.error);
            if (renameData.profile_id) {
                profileId = renameData.profile_id;
                selectedEditingProfileId = profileId;
            }
        }

        const genderSelect = document.getElementById('user-profile-gender-select');
        const raceSelect = document.getElementById('user-profile-race-select');
        const classSelect = document.getElementById('user-profile-class-select');
        const charGender = genderSelect ? genderSelect.value : 'Male';
        const charRace = raceSelect ? raceSelect.value : 'Nord';
        const charClass = classSelect ? classSelect.value : 'Mage';

        const saveRes = await fetch('/api/user_profiles/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_id: profileId,
                content: content,
                gender: charGender,
                race: charRace,
                class: charClass,
                name: newName
            })
        });
        const saveData = await saveRes.json();
        if (saveData.error) throw new Error(saveData.error);

        // Select & activate this profile if not already active
        if (profileId !== activeUserProfile) {
            const selRes = await fetch('/api/user_profiles/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile_id: profileId })
            });
            const selData = await selRes.json();
            if (selData.error) throw new Error(selData.error);
        } else {
            // Already active profile, sync the display attributes
            await fetchCharacterStatus();
        }

        showCustomAlert("Success", `Character profile saved and updated!`);

        await loadUserProfiles();
        await loadHistory();
        closeUserProfileEditor();
    } catch (e) {
        showCustomAlert("Error", e.message || "Failed to update profile.");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = "Save & Apply Profile";
        }
    }
}

// --- createNewUserProfile ---
async function createNewUserProfile() {
    try {
        const res = await fetch('/api/saves/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ character_name: "Eternal Champion", race: "Nord", class: "Mage", gender: "Male" })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const newId = data.save ? data.save.id : 'eternal_champion_001';
        selectedEditingProfileId = newId;

        const messagesList = document.getElementById('messages-list');
        if (messagesList) {
            messagesList.innerHTML = "";
            showWelcomeMessage();
        }

        await loadUserProfiles();
        openUserProfileEditor(newId);
    } catch (e) {
        showCustomAlert("Error", e.message || "Failed to create character.");
    }
}

// --- deleteUserProfileById / deleteSelectedUserProfile ---
async function deleteUserProfileById(targetProfileId) {
    const profileId = targetProfileId || selectedEditingProfileId;
    if (!profileId) return;

    const prof = userProfiles.find(p => p.id === profileId);
    const displayTitle = prof ? prof.name : profileId;
    const isEternal = profileId === 'eternal_champion';

    const confirmTitle = isEternal ? "Reset Character Progress" : "Delete Character";
    const confirmMessage = isEternal 
        ? "Are you sure you want to reset all game progress for Eternal Champion? This will clear stats, inventory, and world history." 
        : `Are you sure you want to permanently delete character '${displayTitle}'?`;

    showCustomConfirm(confirmTitle, confirmMessage, async () => {
        try {
            const res = await fetch('/api/user_profiles/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile_id: profileId })
            });
            const data = await res.json();

            if (data.status === 'success') {
                if (profileId === activeUserProfile || isEternal) {
                    window.location.reload();
                } else {
                    const successTitle = "Character Deleted";
                    const successMsg = `Character '${displayTitle}' has been deleted.`;
                    showCustomAlert(successTitle, successMsg);
                    selectedEditingProfileId = "";
                    closeUserProfileEditor();
                    await loadUserProfiles();
                    await fetchCharacterStatus();
                }
                await loadUserProfiles();
                await fetchCharacterStatus();
            } else {
                showCustomAlert("Error", data.error || "Failed to perform action.");
            }
        } catch (e) {
            showCustomAlert("Error", "Failed to communicate with server.");
        }
    });
}

async function deleteSelectedUserProfile() {
    return deleteUserProfileById(selectedEditingProfileId);
}

/* ==========================================================================
   VI. 5.b SAVE STATES MANAGEMENT
   ========================================================================== */

// New save panel toggle removed as profiles and saves are unified.

// Saves state management functions removed as profiles and saves are unified.


/* ==========================================================================
   VII. 6. PROGRAM / PROGRAM SELECTION
   ========================================================================== */

// --- openAssistantModal ---
async function openAssistantModal(defaultTab = 'program') {
    document.getElementById('assistant-modal').style.display = 'flex';
    switchAssistantModalTab(defaultTab);
    try {
        const res = await fetch('/api/programs');
        const data = await res.json();
        if (data.programs) {
            renderProgramsList(data.programs, data.active);
        }
    } catch (e) {
        console.error("Error loading assistants list:", e);
        showCustomAlert("Error", "Could not fetch program list from server.");
    }
}

// --- closeAssistantModal ---
function closeAssistantModal() {
    document.getElementById('assistant-modal').style.display = 'none';
}

// --- switchAssistantModalTab ---
function switchAssistantModalTab(tab) {
    const compBtn = document.getElementById('assistant-tab-btn-program');
    const userBtn = document.getElementById('assistant-tab-btn-user');
    const sessBtn = document.getElementById('assistant-tab-btn-sessions');
    const compTab = document.getElementById('assistant-tab-content-program');
    const userTab = document.getElementById('assistant-tab-content-user');
    const sessTab = document.getElementById('assistant-tab-content-sessions');
    
    if (!compBtn || !userBtn || !compTab || !userTab) return;
    
    // De-activate all tab buttons by default
    [compBtn, userBtn, sessBtn].forEach(btn => {
        if (btn) {
            btn.style.background = 'hsla(215, 5%, 100%, 0.05)';
            btn.style.color = 'var(--text-muted)';
            btn.style.border = '1px solid hsla(215, 5%, 100%, 0.1)';
        }
    });
    
    // Hide all tab panels by default
    [compTab, userTab, sessTab].forEach(panel => {
        if (panel) panel.style.display = 'none';
    });
    
    if (tab === 'program') {
        compBtn.style.background = 'hsla(215, 5%, 100%, 0.08)';
        compBtn.style.color = 'var(--primary-accent)';
        compBtn.style.border = '1px solid var(--primary-accent)';
        compTab.style.display = 'block';
    } else if (tab === 'user') {
        userBtn.style.background = 'hsla(215, 5%, 100%, 0.08)';
        userBtn.style.color = 'var(--primary-accent)';
        userBtn.style.border = '1px solid var(--primary-accent)';
        userTab.style.display = 'block';
        closeUserProfileEditor();
        loadUserProfiles();
    }
}

// --- openImportProgramModal ---
function openImportProgramModal() {
    closeAssistantModal();
    document.getElementById('import-program-modal').style.display = 'flex';
    
    // Clear inputs
    selectedTavernCardFile = null;
    document.getElementById('tavern-card-input').value = '';
    const nameEl = document.getElementById('tavern-file-name');
    if (nameEl) { nameEl.textContent = '+ Select PNG Card'; nameEl.style.color = ''; nameEl.style.fontWeight = ''; }
    document.getElementById('describe-program-name').value = '';
    document.getElementById('describe-program-desc').value = '';
    switchImportTab('tavern');
}

// --- closeImportProgramModal ---
function closeImportProgramModal() {
    document.getElementById('import-program-modal').style.display = 'none';
}

// --- switchImportTab ---
function switchImportTab(tab) {
    const tabTavern = document.getElementById('import-tab-tavern');
    const tabDescribe = document.getElementById('import-tab-describe');
    const btnTavern = document.getElementById('import-tab-btn-tavern');
    const btnDescribe = document.getElementById('import-tab-btn-describe');
    
    if (tab === 'tavern') {
        tabTavern.style.display = 'block';
        tabDescribe.style.display = 'none';
        btnTavern.style.background = 'hsla(215, 5%, 100%, 0.08)';
        btnTavern.style.color = 'var(--primary-accent)';
        btnTavern.style.border = '1px solid var(--primary-accent)';
        btnDescribe.style.background = 'hsla(215, 5%, 100%, 0.05)';
        btnDescribe.style.color = 'var(--text-muted)';
        btnDescribe.style.border = '1px solid hsla(215, 5%, 100%, 0.1)';
    } else {
        tabTavern.style.display = 'none';
        tabDescribe.style.display = 'block';
        btnTavern.style.background = 'hsla(215, 5%, 100%, 0.05)';
        btnTavern.style.color = 'var(--text-muted)';
        btnTavern.style.border = '1px solid hsla(215, 5%, 100%, 0.1)';
        btnDescribe.style.background = 'hsla(215, 5%, 100%, 0.08)';
        btnDescribe.style.color = 'var(--primary-accent)';
        btnDescribe.style.border = '1px solid var(--primary-accent)';
    }
}

// --- triggerTavernCardFileSelect ---
function triggerTavernCardFileSelect() {
    document.getElementById('tavern-card-input').click();
}

// --- handleTavernCardFileChange ---
function handleTavernCardFileChange(e) {
    const files = e.target.files;
    if (files.length > 0) {
        selectedTavernCardFile = files[0];
        const nameEl = document.getElementById('tavern-file-name');
        if (nameEl) {
            nameEl.textContent = selectedTavernCardFile.name;
            nameEl.style.color = 'var(--primary-accent)';
            nameEl.style.fontWeight = '500';
        }
    }
}

// --- submitTavernCardImport ---
async function submitTavernCardImport() {
    if (!selectedTavernCardFile) {
        showCustomAlert("Error", "Please select a character card PNG image first.");
        return;
    }
    
    const btn = document.getElementById('tavern-import-btn');
    btn.disabled = true;
    btn.textContent = "Importing...";
    
    const formData = new FormData();
    formData.append('card', selectedTavernCardFile);
    formData.append('model', selectedModel);
    
    try {
        const response = await fetch('/api/programs/import/tavern', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        showCustomAlert("Success", `Program '${data.name}' imported successfully!`);
        closeImportProgramModal();
        openAssistantModal();
    } catch (e) {
        showCustomAlert("Error", e.message || "Failed to import character card.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Import Program";
    }
}

// --- submitDescriptionImport ---
async function submitDescriptionImport() {
    const name = document.getElementById('describe-program-name').value.trim();
    const desc = document.getElementById('describe-program-desc').value.trim();
    
    if (!name || !desc) {
        showCustomAlert("Error", "Please provide a name and character description.");
        return;
    }
    
    const btn = document.getElementById('describe-import-btn');
    btn.disabled = true;
    btn.textContent = "Generating Persona...";
    
    try {
        const response = await fetch('/api/programs/import/describe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, description: desc, model: selectedModel })
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        showCustomAlert("Success", `Program '${data.name}' generated successfully!`);
        closeImportProgramModal();
        openAssistantModal();
    } catch (e) {
        showCustomAlert("Error", e.message || "Failed to generate program.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Program";
    }
}

// --- renderProgramsList ---
function renderProgramsList(assistants, activeId) {
    const container = document.getElementById('assistants-list-container');
    container.innerHTML = '';

    // Only show followers who are narratively present (recruited)
    const visible = assistants.filter(a => a.recruited !== false);

    visible.forEach(assistant => {
        const isRia = assistant.id === 'ria_silmane';
        const isActive = (assistant.id === activeId) || assistant.active || (typeof currentAssistantId !== 'undefined' && assistant.id === currentAssistantId) || (typeof activeAssistant !== 'undefined' && activeAssistant && assistant.id === activeAssistant.id);

        const div = document.createElement('div');
        div.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: ${isActive ? 'hsla(var(--gold-h), var(--gold-s), 45%, 0.12)' : 'hsla(215, 5%, 100%, 0.03)'};
            border: 1px solid ${isActive ? 'var(--primary-accent)' : 'var(--border-color)'};
            box-shadow: ${isActive ? '0 0 14px var(--primary-glow)' : 'none'};
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        `;
        div.onmouseover = () => {
            if (!isActive) {
                div.style.background = 'hsla(215, 5%, 100%, 0.07)';
                div.style.borderColor = 'hsla(215, 5%, 100%, 0.2)';
            }
        };
        div.onmouseout = () => {
            if (!isActive) {
                div.style.background = 'hsla(215, 5%, 100%, 0.03)';
                div.style.borderColor = 'var(--border-color)';
            }
        };
        div.onclick = () => selectAssistant(assistant.id);

        const leftArea = document.createElement('div');
        leftArea.style.cssText = 'display: flex; align-items: center; gap: 12px;';

        // Custom program icon image
        const img = document.createElement('img');
        img.className = 'program-list-avatar';
        img.src = `/programs/${assistant.id}/profile.png?t=${profileCacheBuster}`;
        img.alt = assistant.name;
        img.setAttribute('data-name', assistant.name);
        img.setAttribute('data-color', assistant.theme_color || '#4a3520');
        img.style.cssText = `
            width: 44px;
            height: 44px;
            object-fit: cover;
            background: hsla(215, 5%, 100%, 0.05);
            border: 2px solid ${isActive ? 'var(--primary-accent)' : 'var(--border-color)'};
            border-radius: 50%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            flex-shrink: 0;
        `;
        leftArea.appendChild(img);

        const info = document.createElement('div');
        info.style.cssText = 'display: flex; flex-direction: column; gap: 2px;';
        
        const name = document.createElement('div');
        name.style.cssText = 'font-size: 0.95rem; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 8px;';
        name.innerText = assistant.name;

        if (isActive) {
            const activeBadge = document.createElement('span');
            activeBadge.style.cssText = 'font-size: 0.65rem; padding: 2px 7px; border-radius: 10px; background: hsla(var(--gold-h), var(--gold-s), 45%, 0.25); color: var(--gold-bright); border: 1px solid var(--border-color); font-weight: 700; letter-spacing: 0.02em;';
            activeBadge.innerText = 'Active Follower';
            name.appendChild(activeBadge);
        }
        info.appendChild(name);

        const folderName = document.createElement('div');
        folderName.style.cssText = 'font-size: 0.75rem; color: var(--text-muted);';
        folderName.innerText = `id: ${assistant.id}`;
        info.appendChild(folderName);

        leftArea.appendChild(info);
        div.appendChild(leftArea);



        // Edit button
        const editBtn = document.createElement('button');
        editBtn.className = 'action-icon-btn';
        editBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
        `;
        editBtn.title = 'Edit Program Persona';
        editBtn.style.width = '26px';
        editBtn.style.height = '26px';
        editBtn.style.borderRadius = '6px';
        editBtn.style.marginLeft = '8px';
        editBtn.style.flexShrink = '0';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            openProgramProfileModal(assistant.id);
        };
        div.appendChild(editBtn);

        // Ria is immortal — no delete button.
        // Mortal followers get a skull button (permadeath).
        if (!isRia) {
            const skullBtn = document.createElement('button');
            skullBtn.className = 'action-icon-btn';
            skullBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block">
                <path d="M9 18h6M10 22h4M12 2C7.03 2 3 6.03 3 11c0 2.97 1.42 5.6 3.6 7.2V20a1 1 0 0 0 1 1h8.8a1 1 0 0 0 1-1v-1.8C19.58 16.6 21 13.97 21 11c0-4.97-4.03-9-9-9z"/>
                <line x1="9" y1="14" x2="9" y2="14"/><line x1="15" y1="14" x2="15" y2="14"/>
            </svg>`;
            skullBtn.title = 'Kill Follower (Permadeath)';
            skullBtn.style.cssText = 'width:26px;height:26px;border-radius:6px;margin-left:10px;flex-shrink:0;color:var(--danger-color,var(--danger-color));';
            skullBtn.onclick = (e) => {
                e.stopPropagation();
                showCustomConfirm(
                    "Permadeath",
                    `<strong>${assistant.name}</strong> will be permanently removed from your party. This cannot be undone.`,
                    () => deleteAssistant(assistant.id, assistant.name)
                );
            };
            div.appendChild(skullBtn);
        }

        container.appendChild(div);
    });
}

// --- selectAssistant ---
async function selectAssistant(assistantId) {
    try {
        const res = await fetch('/api/programs/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ program_id: assistantId })
        });
        if (!res.ok) {
            const text = await res.text();
            showCustomAlert("Switch Failed", `Server returned status ${res.status}:<br><pre style="font-size: 0.75rem; text-align: left; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; overflow-x: auto; white-space: pre-wrap;">${text}</pre>`);
            return;
        }
        const data = await res.json();
        if (data.status === 'success') {
            closeAssistantModal();
            
            // Reset heart animation class and state to default calm baseline
            const heartElement = document.getElementById('header-heart-pulse') || document.querySelector('.heart-pulse');
            if (heartElement) {
                heartElement.classList.remove('jiggling', 'burst');
                fetchCharacterStatus();
            }
            
            // Reset the chat container and reload history for new assistant
            const chatContainer = document.getElementById('chat-container');
            chatContainer.innerHTML = '';
            
            // Dynamically update UI text properties
            document.title = "LM Arena";
            const h1Element = document.querySelector('header h1');
            if (h1Element) {
                h1Element.innerText = "LM Arena";
            }
            const textarea = document.getElementById('user-input');
            if (textarea) {
                textarea.placeholder = "What do you do?";
            }
            
            // Update profile cache buster and switch avatars instantly
            profileCacheBuster = Date.now();
            updateProfileImages();
            applyTheme(data.active, data.theme);
            
            // Re-request history and dynamic configuration
            modelInitPromise = initializeModelSelect();
            loadHistory();
            loadServerImages();
        } else {
            showCustomAlert("Switch Failed", `Could not select program: ${data.error}`);
        }
    } catch (e) {
        console.error("Error switching assistant:", e);
        showCustomAlert("Error", "Could not connect to the server to switch programs.");
    }
}

// --- deleteAssistant ---
async function deleteAssistant(assistantId, name) {
    showCustomConfirm(
        "Delete Program",
        `Are you sure you want to permanently delete program <strong>${name}</strong>? This will remove all their configs, databank documents, and portraits.`,
        async () => {
            try {
                const res = await fetch('/api/programs/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ program_id: assistantId })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showCustomAlert("Deleted", `Program <strong>${name}</strong> has been deleted.`);
                    if (data.switched_to === 'sebile' || (typeof activeProgram !== 'undefined' && activeProgram === assistantId)) {
                        selectAssistant('sebile');
                    } else {
                        const listRes = await fetch('/api/programs');
                        const listData = await listRes.json();
                        if (listData.programs) {
                            renderProgramsList(listData.programs, listData.active);
                        }
                    }
                } else {
                    showCustomAlert("Error", `Could not delete program: ${data.error}`);
                }
            } catch (e) {
                console.error("Error deleting assistant:", e);
                showCustomAlert("Error", "Could not connect to server to delete program.");
            }
        }
    );
}

// --- PROGRAM PROFILE EDITOR JS METHODS ---
let currentEditingProgramId = null;
let currentEditingProgramOriginalName = '';

async function openProgramProfileModal(programId) {
    currentEditingProgramId = programId;
    closeAssistantModal();
    document.getElementById('program-profile-modal').style.display = 'flex';
    switchProgramProfileTab('core');
    
    // Clear inputs
    document.getElementById('comp-name').value = '';
    document.getElementById('comp-backstory').value = '';
    document.getElementById('comp-directives').value = '';
    document.getElementById('comp-example-msg').value = '';
    document.getElementById('comp-personality-type').value = '';
    document.getElementById('comp-scenario').value = '';
    document.getElementById('comp-tts-voice').value = 'af_heart';
    document.getElementById('comp-image-details').value = '';
    document.getElementById('comp-negative-details').value = '';
    
    try {
        const res = await fetch(`/api/programs/profile?program_id=${programId}&t=${Date.now()}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        
        // v3 fields
        currentEditingProgramOriginalName = data.name || '';
        document.getElementById('comp-name').value = currentEditingProgramOriginalName;
        document.getElementById('comp-personality-type').value = data.personality || '';
        document.getElementById('comp-backstory').value = data.description || '';
        document.getElementById('comp-scenario').value = data.scenario || '';
        document.getElementById('comp-example-msg').value = data.first_mes || '';
        document.getElementById('comp-directives').value = data.system_prompt || '';
        document.getElementById('comp-tts-voice').value = data.tts_voice || 'af_heart';
        
        // Image prompts from extensions.arena
        const arena = (data.extensions || {}).arena || {};
        const imgDetails = arena.image_details || {};
        document.getElementById('comp-image-details').value = imgDetails.positive || '';
        document.getElementById('comp-negative-details').value = imgDetails.negative || '';
        
        await loadProgramJournals();
    } catch (e) {
        console.error('Error loading program profile:', e);
        showCustomAlert('Error', 'Could not load program profile: ' + e.message);
    }
}



    
function closeProgramProfileModal() {
    document.getElementById('program-profile-modal').style.display = 'none';
    openAssistantModal();
}


function switchProgramProfileTab(tab) {
    const tabs = ['core', 'phys'];
    tabs.forEach(t => {
        const content = document.getElementById(`comp-tab-content-${t}`);
        const btn = document.getElementById(`comp-tab-btn-${t}`);
        if (t === tab) {
            if (content) content.style.display = 'block';
            if (btn) {
                btn.style.background = 'hsla(215, 5%, 100%, 0.08)';
                btn.style.color = 'var(--primary-accent)';
                btn.style.border = '1px solid var(--primary-accent)';
            }
        } else {
            if (content) content.style.display = 'none';
            if (btn) {
                btn.style.background = 'hsla(215, 5%, 100%, 0.05)';
                btn.style.color = 'var(--text-muted)';
                btn.style.border = '1px solid hsla(215, 5%, 100%, 0.1)';
            }
        }
    });
}

function exportProgramCard() {
    if (!currentEditingProgramId) return;
    window.location.href = `/api/programs/${encodeURIComponent(currentEditingProgramId)}/export/card`;
}

async function saveProgramProfile() {
    if (!currentEditingProgramId) return;
    
    const newName = document.getElementById('comp-name').value.trim();
    if (!newName) {
        showCustomAlert("Error", "Program Name cannot be empty.");
        return;
    }
    
    let targetProgramId = currentEditingProgramId;
    let wasActive = false;
    
    if (newName !== currentEditingProgramOriginalName) {
        try {
            const renameRes = await fetch('/api/programs/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    program_id: currentEditingProgramId,
                    new_name: newName
                })
            });
            const renameData = await renameRes.json();
            if (renameData.error) {
                showCustomAlert("Rename Failed", renameData.error);
                return;
            }
            targetProgramId = renameData.new_id;
            wasActive = renameData.was_active;
        } catch (e) {
            showCustomAlert("Error", "Failed to rename program: " + e.message);
            return;
        }
    }
    
    const payload = {
        program_id: targetProgramId,
        name: newName,
        tts_voice: document.getElementById('comp-tts-voice').value,
        description: document.getElementById('comp-backstory').value.trim(),
        personality: document.getElementById('comp-personality-type').value.trim(),
        scenario: document.getElementById('comp-scenario').value.trim(),
        first_mes: document.getElementById('comp-example-msg').value.trim(),
        system_prompt: document.getElementById('comp-directives').value.trim(),
        extensions: {
            arena: {
                program_id: targetProgramId,
                image_details: {
                    positive: document.getElementById('comp-image-details').value.trim(),
                    negative: document.getElementById('comp-negative-details').value.trim()
                }
            }
        }
    };
    
    try {
        const res = await fetch('/api/programs/profile/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        document.getElementById('program-profile-modal').style.display = 'none';
        
        // If the edited program is currently active, reload active session details
        const activeProgramText = document.getElementById('user-input');
        if (wasActive || (activeProgramText && (activeProgramText.placeholder.toLowerCase().includes(currentEditingProgramId) || activeProgramText.placeholder.toLowerCase().includes(targetProgramId)))) {
            await selectAssistant(targetProgramId);
        } else {
            openAssistantModal();
        }
    } catch (e) {
        console.error("Error saving program profile:", e);
        showCustomAlert("Error", "Could not save program profile: " + e.message);
    }
}

async function loadProgramJournals() {
    const progId = currentEditingProgramId || (typeof activeProgram !== 'undefined' ? activeProgram : 'ria_silmane');
    if (!progId) return;
    const journalsContainer = document.getElementById('program-journals-list');
    const memoriesContainer = document.getElementById('program-memories-list');
    if (journalsContainer) {
        journalsContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 10px;">Loading journals...</div>';
    }
    if (memoriesContainer) {
        memoriesContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 10px;">Loading memories...</div>';
    }
    
    try {
        // 1. Fetch Keyphrase-Triggered Journals
        const res = await fetch(`/api/programs/journals?program_id=${progId}&t=${Date.now()}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        
        const entries = data.journals || [];
        if (journalsContainer) {
            journalsContainer.innerHTML = '';
            if (entries.length === 0) {
                journalsContainer.innerHTML = '<div class="empty-state">No memory journals saved for this program yet.</div>';
            } else {
                entries.forEach(e => {
                    const row = document.createElement('div');
                    row.className = 'list-entry-row';
                    
                    const header = document.createElement('div');
                    header.className = 'list-entry-header';
                    
                    const kps = document.createElement('span');
                    kps.style.color = 'var(--primary-accent)';
                    kps.style.fontWeight = '600';
                    kps.style.fontSize = '0.72rem';
                    kps.textContent = e.keyphrases ? e.keyphrases.join(', ') : 'no triggers';
                    header.appendChild(kps);
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'action-icon-btn';
                    deleteBtn.innerHTML = `
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    `;
                    deleteBtn.title = 'Delete Journal Entry';
                    deleteBtn.style.width = '26px';
                    deleteBtn.style.height = '26px';
                    deleteBtn.style.borderRadius = '6px';
                    deleteBtn.style.flexShrink = '0';
                    deleteBtn.onclick = () => deleteProgramJournalEntry(e.id);
                    header.appendChild(deleteBtn);
                    
                    row.appendChild(header);
                    
                    const text = document.createElement('div');
                    text.className = 'list-entry-content';
                    let displayContent = e.content || '';
                    const userDisplayName = getUserDisplayName();
                    const programDisplayName = activeProgramName || 'Program';
                    displayContent = displayContent.replace(/\{\{user\}\}/gi, userDisplayName).replace(/\{\{char\}\}/gi, programDisplayName);
                    text.textContent = displayContent;
                    row.appendChild(text);
                    
                    journalsContainer.appendChild(row);
                });
            }
        }
        
        // 2. Fetch Chat Compaction Memories (from memories.json for this program)
        if (memoriesContainer) {
            memoriesContainer.innerHTML = '';
            const memoriesRes = await fetch(`/api/programs/memories?program_id=${currentEditingProgramId}&t=${Date.now()}`);
            const memoriesData = await memoriesRes.json();
            
            const memoryList = memoriesData.memories || [];
            
            if (memoryList.length === 0) {
                memoriesContainer.innerHTML = '<div class="empty-state">No consolidated memories created for this program yet.</div>';
            } else {
                memoryList.forEach(msg => {
                    // Clean up text
                    let cleanText = msg.text || '';
                    if (cleanText.startsWith('[System Memory of older conversation turns]:')) {
                        cleanText = cleanText.replace('[System Memory of older conversation turns]:', '').trim();
                    }
                    
                    const row = document.createElement('div');
                    row.className = 'list-entry-row';
                    
                    const header = document.createElement('div');
                    header.className = 'list-entry-header';
                    
                    const kps = document.createElement('span');
                    kps.style.color = 'hsl(115, 80%, 40%)';
                    kps.style.fontWeight = '600';
                    kps.style.fontSize = '0.72rem';
                    kps.textContent = 'Auto-Compacted';
                    header.appendChild(kps);
                    
                    // Right side container for timestamp and delete button
                    const rightContainer = document.createElement('div');
                    rightContainer.style.cssText = 'display: flex; align-items: center; gap: 8px;';
                    
                    if (msg.timestamp) {
                        const tsSpan = document.createElement('span');
                        tsSpan.style.cssText = 'color: var(--text-muted); font-size: 0.7rem;';
                        const d = new Date(msg.timestamp * 1000);
                        tsSpan.textContent = d.toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
                        rightContainer.appendChild(tsSpan);
                    }
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'action-icon-btn';
                    deleteBtn.innerHTML = `
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    `;
                    deleteBtn.title = 'Delete Compacted Memory';
                    deleteBtn.style.width = '26px';
                    deleteBtn.style.height = '26px';
                    deleteBtn.style.borderRadius = '6px';
                    deleteBtn.style.flexShrink = '0';
                    deleteBtn.onclick = () => deleteConsolidatedMemory(msg.session_id, msg.timestamp);
                    rightContainer.appendChild(deleteBtn);
                    
                    header.appendChild(rightContainer);
                    row.appendChild(header);
                    
                    const text = document.createElement('div');
                    text.className = 'list-entry-content italic';
                    let displayMem = cleanText;
                    const userDisplayName = getUserDisplayName();
                    const programDisplayName = activeProgramName || 'Program';
                    displayMem = displayMem.replace(/\{\{user\}\}/gi, userDisplayName).replace(/\{\{char\}\}/gi, programDisplayName);
                    text.textContent = displayMem;
                    row.appendChild(text);
                    
                    memoriesContainer.appendChild(row);
                });
            }
        }
        
    } catch (e) {
        console.error("Error in loadProgramJournals:", e);
        if (journalsContainer) {
            journalsContainer.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.75rem; text-align: center; padding: 10px;">Failed to load journals.</div>';
        }
        if (memoriesContainer) {
            memoriesContainer.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.75rem; text-align: center; padding: 10px;">Failed to load memories.</div>';
        }
    }
}

async function addManualJournalEntry() {
    if (!currentEditingProgramId) return;
    const kpInput = document.getElementById('journal-keyphrases-input');
    const cInput = document.getElementById('journal-content-input');
    if (!kpInput || !cInput) return;
    
    const keyphrases = kpInput.value.trim();
    const content = cInput.value.trim();
    if (!keyphrases || !content) {
        showCustomAlert("Error", "Please provide trigger keywords and memory content.");
        return;
    }
    
    try {
        const res = await fetch('/api/programs/journals/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                program_id: currentEditingProgramId,
                keyphrases: keyphrases,
                content: content
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        
        kpInput.value = '';
        cInput.value = '';
        await loadProgramJournals();
    } catch (e) {
        showCustomAlert("Error", "Could not add journal: " + e.message);
    }
}

async function deleteProgramJournalEntry(entryId) {
    if (!currentEditingProgramId) return;
    showCustomConfirm(
        "Delete Memory Entry",
        "Are you sure you want to permanently delete this memory entry? The program will forget this context immediately.",
        async () => {
            try {
                const res = await fetch('/api/programs/journals/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        program_id: currentEditingProgramId,
                        id: entryId
                    })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                await loadProgramJournals();
            } catch (e) {
                showCustomAlert("Error", "Could not delete memory entry: " + e.message);
            }
        }
    );
}

async function deleteConsolidatedMemory(session_id, timestamp) {
    showCustomConfirm(
        "Delete Consolidated Memory",
        "Are you sure you want to permanently delete this compacted chat history block? Your program will lose this memory immediately.",
        async () => {
            try {
                const res = await fetch('/api/programs/memories/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: session_id || sessionId,
                        timestamp: timestamp
                    })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                await loadProgramJournals();
            } catch (e) {
                showCustomAlert("Error", "Could not delete memory: " + e.message);
            }
        }
    );
}

/* ==========================================================================
   VIII. 7. CHAT SESSION & HISTORY CONTROLS
   ========================================================================== */

// --- getUserDisplayName ---
function getUserDisplayName() {
    return activePlayerName || currentCharacterData?.character?.name || window.__ARENA_CONFIG?.userName || "Eternal Champion";
}

// --- renderOpeningLoreCard ---
function renderOpeningLoreCard() {
    const container = document.getElementById('chat-container');
    if (!container) return;
    if (document.getElementById('opening-lore-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'opening-lore-banner';
    banner.className = 'opening-lore-overlay';
    banner.innerHTML = `
        <div class="opening-lore-card">
            <div class="opening-lore-heading">
                <span class="opening-lore-subtitle">THE ELDER SCROLLS</span>
                <h2 class="opening-lore-title">ARENA</h2>
            </div>
            <div class="opening-lore-divider"></div>
            <div class="opening-lore-body">
                <p>For centuries different factions battled in petty wars and border conflicts, until in 2E 896 Tiber Septim crushed all who opposed him and proclaimed himself Emperor. Still, the bitter years of war had their effect. The name Tamriel — Elvish for <em>&ldquo;Dawn's Beauty&rdquo;</em> — seldom fell from anguished lips and was soon forgotten. In a place where life and death were different sides of the same coin, tossed every day, the people began calling the land of their sorrow the Arena.</p>
                <p>492 years after Tiber Septim brought peace, a shadow fell. The Emperor Uriel Septim VII celebrated his forty third birthday, but jealous hearts desired the throne and plotted his downfall.</p>
                <p>Uriel Septim VII stood with Talin, captain of the Imperial Guard, summoned to the throne room by Jagar Tharn on rumors of treachery. But Tharn betrayed the Emperor. He took the throne and wasted no time. The Emperor's Guard were twisted into loyal servants, and the Imperial Wizard settled into his stolen crown.</p>
                <p class="opening-lore-climax">It is said that hope flies on death's wings. Prepare then — for as the Elder Scrolls foretold, it is here that your adventure begins.</p>
            </div>
        </div>
    `;

    if (container.firstChild) {
        container.insertBefore(banner, container.firstChild);
    } else {
        container.appendChild(banner);
    }
}

// --- showWelcomeMessage ---
function showWelcomeMessage() {
    renderOpeningLoreCard();
    // Do not show welcome message if there is already active chat history visible
    const visibleMessages = chatContainer.querySelectorAll('.message-row:not(#welcome-message):not(#onboarding-container)');
    if (visibleMessages.length > 0) return;

    let welcome = document.getElementById('welcome-message');
    const displayUser = getUserDisplayName();
    const greetingText = programWelcomeMessage || ("Hello, " + "{" + "{" + "user" + "}" + "}.");
    const resolvedGreeting = replacePlaceholders(greetingText);
    
    let parsedText = resolvedGreeting;
    if (typeof marked !== 'undefined' && marked.parse) {
        try {
            parsedText = marked.parse(resolvedGreeting);
        } catch (e) {
            console.error("Error parsing welcome markdown:", e);
        }
    } else {
        parsedText = `<p>${resolvedGreeting}</p>`;
    }

    if (!welcome) {
        welcome = document.createElement('div');
        welcome.className = 'message-row program-row';
        welcome.id = 'welcome-message';
        const profileUrl = getProfileUrl();
        welcome.innerHTML = `
            <div class="avatar-container">
                <img class="avatar program-avatar" src="${profileUrl}" alt="Program" onclick="expandImage('${profileUrl}')">
            </div>
            <div class="message program">
                <div class="message-text">
                    ${parsedText}
                </div>
            </div>
        `;
        chatContainer.appendChild(welcome);
    } else {
        const textDiv = welcome.querySelector('.message-text');
        if (textDiv) {
            textDiv.innerHTML = parsedText;
        }
    }
}

// --- loadHistory ---
async function loadHistory() {
    try {
        const container = document.getElementById('chat-container');
        if (container) {
            container.classList.remove('smooth-scroll');
        }

        // If the session ID came from localStorage, verify it still exists on the server.
        // If it is missing, default to 'default'.
        if (!sessionFromUrl && sessionId !== 'default') {
            try {
                const res = await fetch('/api/sessions');
                const data = await res.json();
                if (data.sessions && !data.sessions.includes(sessionId)) {
                    console.warn(`Last opened session "${sessionId}" is missing on the server. Falling back to default.`);
                    sessionId = 'default';
                    safeLocalStorage.setItem('program_session_id', 'default');
                    
                    // Update the UI header ID display if it exists
                    const sessionDisplay = document.getElementById('session-id-display');
                    if (sessionDisplay) {
                        sessionDisplay.textContent = `• ID: ${sessionId.slice(-4)}`;
                        sessionDisplay.title = `Full Session ID: ${sessionId}`;
                    }
                }
            } catch (err) {
                console.error("Error verifying last opened session:", err);
            }
        }

        // Trigger server images in background without blocking history load
        loadServerImages();
        const historyRes = await fetch(`/history?session_id=${sessionId}&t=${Date.now()}`);
        const data = await historyRes.json();
        if (data.welcome_message) {
            programWelcomeMessage = data.welcome_message;
        } else {
            programWelcomeMessage = null;
        }
        if (data.user_name) {
            activePlayerName = data.user_name;
        }
        if (data.active_program) {
            applyTheme(data.active_program, data.theme);
        }
        if (data.character_name) {
            activeProgramName = data.character_name;
            const programTitle = "LM Arena";
            document.title = programTitle;
            
            const headerTitle = document.querySelector('.header-title-area h1');
            if (headerTitle) {
                headerTitle.textContent = programTitle;
            }
            
            const userInput = document.getElementById('user-input');
            if (userInput) {
                userInput.placeholder = "What do you do?";
            }
        }
        
        if (container) {
            container.innerHTML = '';
        }
        renderOpeningLoreCard();
        if (data.history && data.history.length > 0) {
            // Remove welcome message or onboarding card
            const welcome = document.getElementById('welcome-message');
            if (welcome) welcome.remove();
            const onboarding = document.getElementById('onboarding-container');
            if (onboarding) onboarding.remove();
            
            // Render history
            (data.history || []).forEach(msg => {
                renderMessage(msg);
            });

            // Check if latest message is a pending player skill check
            evaluateLatestMessageForSkillCheck();
            updateMusicFromWorldState();
        } else {
            // History is empty! Wait for model initialization and health checks to complete if they haven't yet
            if (modelInitPromise) {
                try {
                    // Wait at most 2 seconds for model initialization status
                    await Promise.race([
                        modelInitPromise,
                        new Promise(resolve => setTimeout(resolve, 2000))
                    ]);
                } catch (e) {
                    console.error("Error waiting for modelInitPromise in empty history block:", e);
                }
            }

            // Check connection status
            if (!connectionStatus.remote_configured  && !connectionStatus.local_online) {
                showOnboardingCard();
            } else {
                showWelcomeMessage();
                // On a new chat session (no history), default to local model
                const defaultModel = safeLocalStorage.getItem('program_default_model') || 'local-llm';
                selectedModel = defaultModel;
                safeLocalStorage.setItem('program_selected_model', selectedModel);
                const modelSelectElement = document.getElementById('model-select');
                if (modelSelectElement) {
                    modelSelectElement.value = selectedModel;
                }
            }
        }
        fetchCharacterStatus();

        // Restore scroll position
        if (container) {
            const savedScrollPos = safeSessionStorage.getItem('chat_scroll_pos');
            const wasAtBottom = safeSessionStorage.getItem('chat_was_at_bottom');

            if (wasAtBottom === 'true' || wasAtBottom === null) {
                container.scrollTop = container.scrollHeight;
                isAtBottom = true;
            } else if (savedScrollPos) {
                container.scrollTop = parseInt(savedScrollPos, 10);
                isAtBottom = false;
            }
        }
    } catch (error) {
        console.error("Error loading chat history:", error);
        // Ensure modelInitPromise finishes so connectionStatus is populated (max 1.5 seconds)
        if (modelInitPromise) {
            try {
                await Promise.race([
                    modelInitPromise,
                    new Promise(resolve => setTimeout(resolve, 1500))
                ]);
            } catch (e) {}
        }
        if (!connectionStatus.remote_configured  && !connectionStatus.local_online) {
            showOnboardingCard();
        } else {
            showWelcomeMessage();
        }
    } finally {
        // Re-enable smooth scroll after a brief delay to avoid animating the initial position
        setTimeout(() => {
            const container = document.getElementById('chat-container');
            if (container) {
                container.classList.add('smooth-scroll');
            }
        }, 50);
        hideLoadingOverlay();
        if (typeof startSSE === 'function') {
            startSSE();
        }
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('chat-loading-overlay');
    if (overlay && !overlay.classList.contains('fade-out')) {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }, 400);
    }
}

// --- resetSession ---
async function resetSession() {
    showCustomConfirm("Reset Session", "Are you sure you want to reset the chat session and clear the context window?", async () => {
        try {
            await fetch('/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
        } catch (e) {
            console.error("Failed to reset session on server:", e);
        }
        localStorage.removeItem('program_session_id');
        localStorage.removeItem('program_selected_model');
        reloadApp(true, true);
    });
}

/* ==========================================================================
   IX. 8. MESSAGE RENDERING & POST-PROCESSING
   ========================================================================== */

// --- toggleAutoSpeak ---
function toggleAutoSpeak() {
    ttsAutoSpeak = !ttsAutoSpeak;
    const btn = document.getElementById('tts-toggle-btn');
    if (btn) {
        if (ttsAutoSpeak) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
            if (currentAudio) {
                currentAudio.pause();
            }
            resetSpeakButtons();
        }
    }
}

// --- resetSpeakButtons ---
function resetSpeakButtons() {
    document.querySelectorAll('.speak-btn').forEach(btn => {
        btn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
        `;
        btn.title = "Read Message";
    });
    currentPlayingBtn = null;
}

// --- speakMessage ---
async function speakMessage(btn) {
    const bubble = btn.closest('.message');
    if (!bubble) return;
    
    const msgId = bubble.dataset.msgId;
    let rawText = bubble.dataset.rawText || '';
    
    // Clean up thinking block before speaking
    rawText = rawText.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
    
    // If already playing this message, pause it
    if (currentPlayingBtn === btn) {
        if (currentAudio) {
            currentAudio.pause();
        }
        resetSpeakButtons();
        return;
    }
    
    // Stop any current playback
    if (currentAudio) {
        currentAudio.pause();
    }
    resetSpeakButtons();
    
    // Set loading state
    currentPlayingBtn = btn;
    btn.title = "Synthesizing speech...";
    btn.innerHTML = `
        <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="2" x2="12" y2="6"></line>
            <line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line>
            <line x1="18" y1="12" x2="22" y2="12"></line>
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
        </svg>
    `;
    
    try {
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: msgId, text: rawText })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'TTS request failed');
        }
        
        // Play audio
        currentAudio = new Audio(data.audio_url);
        currentAudio.volume = isSpeechMuted ? 0 : speechVolume;
        currentAudio.onended = () => {
            resetSpeakButtons();
        };
        currentAudio.onerror = () => {
            showCustomAlert("Playback Error", "Audio playback failed.");
            resetSpeakButtons();
        };
        
        // Update button to pause state
        btn.title = "Pause speech";
        btn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
        `;
        
        await currentAudio.play();
    } catch (err) {
        console.error("TTS generation/playback error:", err);
        showCustomAlert("Speech Synthesis Failed", "Speech synthesis failed: " + err.message);
        resetSpeakButtons();
    }
}
// --- toggleThinkingBlock ---
function toggleThinkingBlock(headerElement) {
    const body = headerElement.nextElementSibling;
    const chevron = headerElement.querySelector('.thinking-block-chevron');
    body.classList.toggle('expanded');
    chevron.textContent = body.classList.contains('expanded') ? '▲' : '▼';
}

// --- formatMessageTimestamp ---
function formatMessageTimestamp(timestamp, msg = null) {
    if (msg && msg.tamrielic_date) {
        if (typeof msg.tamrielic_date === 'string') {
            return msg.tamrielic_date;
        }
        if (typeof msg.tamrielic_date === 'object') {
            const t = msg.tamrielic_date;
            const timeStr = t.hour !== undefined ? ` • ${formatTamrielicTime(t.hour)}` : '';
            return `${t.day || 1} ${t.month || 'Morning Star'}, ${t.year ? `3E ${t.year}` : '3E 389'}${timeStr}`;
        }
    }

    // Extract historical date header from text if present (e.g. **1st of Hearthfire, 3E 389**)
    if (msg && msg.text) {
        const dateMatch = msg.text.match(/\*\*(\d+(?:st|nd|rd|th)?\s+(?:of\s+)?[A-Za-z\s]+,\s*3E\s*\d+)\*\*/i);
        if (dateMatch) {
            return `${dateMatch[1]} • 6:00 AM`;
        }
    }

    const world = currentCharacterData?.world;
    if (world) {
        const tDate = world.date || world.tamrielic_date || { day: 1, month: "Morning Star", year: 389, hour: 6 };
        const timeStr = tDate.hour !== undefined ? ` • ${formatTamrielicTime(tDate.hour)}` : '';
        return `${tDate.day || 1} ${tDate.month || 'Morning Star'}, ${tDate.year ? `3E ${tDate.year}` : '3E 389'}${timeStr}`;
    }

    return "1 Morning Star, 3E 389 • 6:00 AM";
}

// --- renderCompletedLogs ---
function renderCompletedLogs(bubble, toolCalls, duration = null) {
    if (!toolCalls || toolCalls.length === 0) return;

    let logsContainer = bubble.querySelector('.antigravity-logs-container');
    if (logsContainer) {
        logsContainer.innerHTML = '';
    } else {
        logsContainer = document.createElement('div');
        logsContainer.className = 'antigravity-logs-container';
        bubble.appendChild(logsContainer);
    }

    const pairedTools = [];
    const callsMap = {};
    const seenCallSignatures = new Set();
    
    toolCalls.forEach(tc => {
        if (tc.type === 'call') {
            const sig = tc.name + '::' + JSON.stringify(tc.args || {});
            if (seenCallSignatures.has(sig)) return;
            seenCallSignatures.add(sig);
            const callInfo = {
                id: tc.id,
                name: tc.name,
                args: tc.args,
                response: null
            };
            pairedTools.push(callInfo);
            callsMap[tc.id] = callInfo;
        } else if (tc.type === 'response') {
            if (callsMap[tc.id]) {
                callsMap[tc.id].response = tc.response;
            } else {
                pairedTools.push({
                    id: tc.id,
                    name: tc.name,
                    args: null,
                    response: tc.response
                });
            }
        }
    });

    if (pairedTools.length > 0) {
        const getBasename = (pathStr) => {
            if (!pathStr) return '';
            if (pathStr.startsWith('http://') || pathStr.startsWith('https://')) {
                try {
                    const url = new URL(pathStr);
                    return url.hostname + url.pathname;
                } catch(e) {
                    return pathStr;
                }
            }
            const parts = pathStr.split(/[\\/]/);
            return parts[parts.length - 1] || pathStr;
        };

        const parseResultCount = (toolName, responseText) => {
            if (!responseText) return null;
            const trimmed = responseText.trim();
            if (trimmed === "No search results found." || trimmed === "No search results found") {
                return 0;
            }
            if (trimmed.startsWith("Error")) {
                return 0;
            }
            try {
                if (trimmed.startsWith('{') || trimmed.trim().startsWith('[')) {
                    const parsed = JSON.parse(trimmed);
                    if (Array.isArray(parsed)) return parsed.length;
                    if (parsed.results && Array.isArray(parsed.results)) return parsed.results.length;
                    if (parsed.matches && Array.isArray(parsed.matches)) return parsed.matches.length;
                }
            } catch(e) {}
            
            if (toolName === 'web_search' || toolName === 'google_search') {
                const blocks = responseText.split('\n\n').filter(b => b.trim().length > 0);
                return blocks.length;
            }
            
            const lines = responseText.split('\n').filter(l => l.trim().length > 0);
            if (lines.length > 0 && lines.length < 50) {
                return lines.length;
            }
            return null;
        };

        const escapeHtml = (text) => {
            if (!text) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        };

        const createLogItemElement = (item) => {
            const itemEl = document.createElement('div');
            itemEl.className = 'antigravity-log-item';
            itemEl.innerHTML = `
                <span class="ag-log-icon">${item.icon}</span>
                <span class="ag-log-action">${item.action}</span>
                <span class="ag-log-target">${item.target}</span>
                <span class="ag-log-suffix">${item.suffix}</span>
            `;

            const detailEl = document.createElement('div');
            detailEl.className = 'antigravity-log-detail';
            detailEl.style.display = 'none';
            
            let argsFormatted = '';
            if (item.args && Object.keys(item.args).length > 0) {
                argsFormatted = `Parameters:\n${JSON.stringify(item.args, null, 2)}\n\n`;
            }
            
            let responseText = item.response || 'No response data';
            
            detailEl.innerHTML = `
                <pre><code>${argsFormatted}Response:\n${escapeHtml(responseText)}</code></pre>
            `;

            itemEl.onclick = (e) => {
                e.stopPropagation();
                const isExpanded = detailEl.style.display === 'block';
                detailEl.style.display = isExpanded ? 'none' : 'block';
            };

            return { item: itemEl, detail: detailEl };
        };

        const formattedItems = pairedTools.map(tool => {
            let category = 'explore';
            let icon = getLogIconSvg('file');
            let action = 'Analyzed';
            let target = '';
            let suffix = '';
            let isMutation = false;
            
            const name = tool.name;
            const args = tool.args || {};
            
            if (name === 'read_file' || name === 'view_file' || name === 'read_webpage') {
                category = 'file';
                icon = name === 'read_webpage' ? getLogIconSvg('webpage') : getLogIconSvg('file');
                action = 'Analyzed';
                
                let pathVal = args.path || args.AbsolutePath || args.url || '';
                target = getBasename(pathVal);
                
                let start = args.StartLine || args.start_line || '';
                let end = args.EndLine || args.end_line || '';
                if (start && end) {
                    suffix = ` #L${start}-${end}`;
                } else if (start) {
                    suffix = ` #L${start}`;
                }
            } 
            else if (name === 'get_workspace_structure' || name === 'list_dir') {
                category = 'folder';
                icon = getLogIconSvg('folder');
                action = 'Analyzed';
                let pathVal = args.path || args.DirectoryPath || '';
                target = pathVal || 'workspace';
                suffix = ' >';
            }
            else if (name === 'search_codebase' || name === 'grep_search' || name === 'web_search' || name === 'google_search' || name === 'search_github' || name === 'search_arxiv' || name === 'search_hacker_news') {
                category = 'search';
                icon = getLogIconSvg('search');
                action = 'Searched';
                target = args.query || args.keyword || args.Query || '';
                
                if (tool.response) {
                    let count = parseResultCount(tool.name, tool.response);
                    if (count !== null) {
                        suffix = ` ${count} result${count !== 1 ? 's' : ''}`;
                    }
                }
            }
            else if (name === 'write_file' || name === 'write_to_file') {
                category = 'edit';
                icon = getLogIconSvg('edit');
                isMutation = true;
                
                let pathVal = args.path || args.TargetFile || '';
                target = getBasename(pathVal);
                
                let contentVal = args.content || args.CodeContent || '';
                let linesCount = contentVal ? contentVal.split('\n').length : 0;
                
                action = args.Overwrite ? 'Edited' : 'Created';
                suffix = ` +${linesCount} -0`;
            }
            else if (name === 'replace_in_file' || name === 'replace_file_content' || name === 'multi_replace_file_content') {
                category = 'edit';
                icon = getLogIconSvg('edit');
                isMutation = true;
                
                let pathVal = args.path || args.TargetFile || '';
                target = getBasename(pathVal);
                action = 'Edited';
                
                let linesAdded = 0;
                let linesRemoved = 0;
                if (name === 'replace_file_content' && args.ReplacementContent) {
                    linesAdded = args.ReplacementContent.split('\n').length;
                }
                if (name === 'replace_file_content' && args.TargetContent) {
                    linesRemoved = args.TargetContent.split('\n').length;
                }
                
                if (linesAdded || linesRemoved) {
                    suffix = ` +${linesAdded} -${linesRemoved}`;
                }
            }
            else if (name === 'run_shell_command' || name === 'run_command') {
                category = 'command';
                icon = getLogIconSvg('command');
                isMutation = true;
                action = 'Ran';
                target = args.command || args.CommandLine || '';
                if (target.length > 50) {
                    target = target.substring(0, 47) + '...';
                }
            }
            else {
                category = 'other';
                icon = getLogIconSvg('gear');
                action = 'Ran';
                target = name;
                isMutation = true;
            }
            
            return {
                id: tool.id || 'call_' + Math.random().toString(36).substring(2, 6),
                name: tool.name,
                args: tool.args,
                response: tool.response,
                category,
                icon,
                action,
                target,
                suffix,
                isMutation
            };
        });

        const explorationItems = formattedItems.filter(item => !item.isMutation);
        const mutationItems = formattedItems.filter(item => item.isMutation);

        const uniqueFiles = new Set();
        const uniqueFolders = new Set();
        let searchesCount = 0;

        explorationItems.forEach(item => {
            if (item.category === 'file') {
                uniqueFiles.add(item.target);
            } else if (item.category === 'folder') {
                uniqueFolders.add(item.target);
            } else if (item.category === 'search') {
                searchesCount++;
            }
        });

        const filesCount = uniqueFiles.size;
        const foldersCount = uniqueFolders.size;
        const parts = [];
        if (filesCount > 0) parts.push(`${filesCount} file${filesCount > 1 ? 's' : ''}`);
        if (foldersCount > 0) parts.push(`${foldersCount} folder${foldersCount > 1 ? 's' : ''}`);
        if (searchesCount > 0) parts.push(`${searchesCount} search${searchesCount > 1 ? 'es' : ''}`);

        const subheaderText = parts.length > 0 ? `Explored ${parts.join(', ')}` : 'Explored workspace';

        const logsCard = document.createElement('div');
        logsCard.className = 'antigravity-logs-card';

        const header = document.createElement('div');
        header.className = 'antigravity-logs-header';
        const durationText = duration ? `Worked for ${duration}s` : 'Activity Log';
        header.innerHTML = `
            <span class="ag-timer-icon">${getLogIconSvg('timer')}</span>
            <span>${durationText}</span>
            <span class="ag-header-chevron">▼</span>
        `;

        const body = document.createElement('div');
        body.className = 'antigravity-logs-body';
        body.style.display = 'none';

        if (explorationItems.length > 0) {
            const exploreContainer = document.createElement('div');
            exploreContainer.className = 'antigravity-explore-container';

            const exploreHeader = document.createElement('div');
            exploreHeader.className = 'antigravity-explore-header';
            exploreHeader.innerHTML = `
                <span>${subheaderText}</span>
                <span class="ag-explore-chevron">▼</span>
            `;

            const exploreBody = document.createElement('div');
            exploreBody.className = 'antigravity-explore-body';
            exploreBody.style.display = 'none';

            explorationItems.forEach(item => {
                const itemEl = createLogItemElement(item);
                exploreBody.appendChild(itemEl.item);
                exploreBody.appendChild(itemEl.detail);
            });

            exploreHeader.onclick = (e) => {
                e.stopPropagation();
                const isExpanded = exploreBody.style.display === 'flex' || exploreBody.style.display === 'block';
                exploreBody.style.display = isExpanded ? 'none' : 'flex';
                exploreHeader.querySelector('.ag-explore-chevron').classList.toggle('expanded', !isExpanded);
            };

            exploreContainer.appendChild(exploreHeader);
            exploreContainer.appendChild(exploreBody);
            body.appendChild(exploreContainer);
        }

        mutationItems.forEach(item => {
            const itemEl = createLogItemElement(item);
            itemEl.item.classList.add('mutation-item');
            body.appendChild(itemEl.item);
            body.appendChild(itemEl.detail);
        });

        header.onclick = () => {
            const isExpanded = body.style.display === 'flex' || body.style.display === 'block';
            body.style.display = isExpanded ? 'none' : 'flex';
            header.querySelector('.ag-header-chevron').classList.toggle('expanded', !isExpanded);
        };

        logsCard.appendChild(header);
        logsCard.appendChild(body);
        logsContainer.appendChild(logsCard);
    }
}

// --- computeContentHash ---
function computeContentHash(msg) {
    const str = JSON.stringify([
        msg.id,
        msg.role,
        msg.text,
        (msg.media || []).map(m => m.url),
        (msg.tool_calls || []).map(t => t.id),
        msg.timestamp
    ]);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash = hash & hash;
    }
    return 'h_' + Math.abs(hash).toString(36);
}

// --- normalizeChatResponse ---
function normalizeChatResponse(data) {
    const text = data.response || '';
    const media = [];
    
    // Extract markdown images
    const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    let match;
    let cleanText = text;
    while ((match = imgRegex.exec(text)) !== null) {
        const url = match[2];
        media.push({
            url: url,
            type: url.toLowerCase().endsWith('.mp4') ? 'video' : 'image'
        });
    }
    cleanText = text.replace(imgRegex, '').trim();

    // Determine portrait/image prompt from tool calls
    let imagePrompt = null;
    const toolCalls = data.tool_calls || [];
    const imgCall = toolCalls.find(tc => tc.type === 'call' && [
        'generate_program_portrait', 'generate_local_image',
        'generate_imagen', 'generate_general_image'
    ].includes(tc.name));
    if (imgCall && imgCall.args && imgCall.args.prompt) {
        imagePrompt = imgCall.args.prompt;
    }

    if (imagePrompt) {
        media.forEach(m => {
            m.prompt = imagePrompt;
        });
    }

    return {
        id: data.program_msg_id,
        role: 'program',
        text: cleanText,
        media: media,
        tool_calls: toolCalls,
        timestamp: data.timestamp,
        duration: data.duration,
        editable: true,
        deletable: true
    };
}

// --- renderVoiceCallRow ---
function renderVoiceCallRow(msg) {
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();
    const onboarding = document.getElementById('onboarding-container');
    if (onboarding) onboarding.remove();

    const row = document.createElement('div');
    row.className = 'message-row voice-call-row';
    row.dataset.role = 'voice-call';
    row.dataset.rawText = msg.text || '';
    row.dataset.timestamp = msg.timestamp || '';
    row.dataset.msgId = msg.id || generateMessageId(msg.text, 'voice-call');
    row.dataset.contentHash = computeContentHash(msg);

    let transcriptData = { duration: '0s', turns: [] };
    try {
        transcriptData = JSON.parse(msg.text);
    } catch(e) {
        console.error("Error parsing voice call transcript json:", e);
    }

    const card = document.createElement('div');
    card.className = 'voice-call-record';
    
    const cardHeader = document.createElement('div');
    cardHeader.className = 'voice-call-record-header';
    
    const headerInfo = document.createElement('div');
    headerInfo.className = 'voice-call-record-info';
    
    const iconDiv = document.createElement('div');
    iconDiv.className = 'voice-call-record-icon';
    iconDiv.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
        </svg>
    `;
    
    const textDiv = document.createElement('div');
    const title = document.createElement('h4');
    title.className = 'voice-call-record-title';
    title.textContent = `Voice Call with ${activeProgramName || 'Program'}`;
    
    const meta = document.createElement('p');
    meta.className = 'voice-call-record-meta';
    const turnCount = transcriptData.turns ? transcriptData.turns.length : 0;
    meta.textContent = `Duration: ${transcriptData.duration || '0s'} • ${turnCount} turn${turnCount !== 1 ? 's' : ''}`;
    
    textDiv.appendChild(title);
    textDiv.appendChild(meta);
    headerInfo.appendChild(iconDiv);
    headerInfo.appendChild(textDiv);
    
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'voice-call-record-toggle';
    toggleBtn.textContent = 'Show Transcript';
    
    cardHeader.appendChild(headerInfo);
    cardHeader.appendChild(toggleBtn);
    card.appendChild(cardHeader);
    
    const hoverActions = document.createElement('div');
    hoverActions.className = 'voice-call-actions';
    
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'action-icon-btn';
    deleteBtn.title = 'Delete Call Record';
    deleteBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
    `;
    deleteBtn.onclick = () => deleteTurnFromMessage(deleteBtn);
    hoverActions.appendChild(deleteBtn);
    card.appendChild(hoverActions);
    
    const transcriptDiv = document.createElement('div');
    transcriptDiv.className = 'voice-call-record-transcript';
    transcriptDiv.style.display = 'none';
    
    if (transcriptData.turns && transcriptData.turns.length > 0) {
        transcriptData.turns.forEach(turn => {
            const turnP = document.createElement('p');
            turnP.className = 'voice-call-record-turn';
            
            const speakerSpan = document.createElement('span');
            speakerSpan.className = `turn-speaker ${turn.speaker}`;
            speakerSpan.textContent = turn.speaker === 'user' ? `${getUserDisplayName()}:` : `${activeProgramName || 'Program'}:`;
            
            const textSpan = document.createElement('span');
            textSpan.textContent = ` ${turn.text}`;
            
            turnP.appendChild(speakerSpan);
            turnP.appendChild(textSpan);
            transcriptDiv.appendChild(turnP);
        });
    } else {
        const noTurnsP = document.createElement('p');
        noTurnsP.className = 'voice-call-record-turn';
        noTurnsP.style.fontStyle = 'italic';
        noTurnsP.textContent = 'No dialogue recorded.';
        transcriptDiv.appendChild(noTurnsP);
    }
    
    card.appendChild(transcriptDiv);
    row.appendChild(card);
    
    toggleBtn.onclick = () => {
        if (transcriptDiv.style.display === 'none') {
            transcriptDiv.style.display = 'flex';
            toggleBtn.textContent = 'Hide Transcript';
        } else {
            transcriptDiv.style.display = 'none';
            toggleBtn.textContent = 'Show Transcript';
        }
    };
    
    chatContainer.appendChild(row);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return row;
}

// --- renderMessage ---
function renderMessage(msg, isLive = false) {
    if (msg.role === 'voice-call') {
        return renderVoiceCallRow(msg);
    }

    const role = msg.role;
    const text = msg.text || '';
    const msgId = msg.id || generateMessageId(text, role);

    // Client-side hidden prefix check
    const _hiddenPrefixes = ['port_', 'quest_', 'tool_'];
    if (msg.id && _hiddenPrefixes.some(p => msg.id.startsWith(p))) return null;
    if (text && (text.includes("Send me a portrait of yourself") || text.includes("[GENERATE_IMAGE:") || text.includes("[GENERATE_IMAGEN:"))) return null;

    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();
    const onboarding = document.getElementById('onboarding-container');
    if (onboarding) onboarding.remove();

    const isMsgTransient = msg.isTransient || (role === 'program' && (
        text === '*(Generation stopped)*' || 
        text === '*(Generation cancelled)*' || 
        text === 'Error connecting to the Arena.' ||
        text === 'The Arena is taking a while to restart. Please refresh manually.' ||
        (!msg.timestamp && !isLive && text.includes('Error'))
    ));

    // Extract portrait prompt
    let portraitPrompt = null;
    if (msg.tool_calls && msg.tool_calls.length > 0) {
        const call = msg.tool_calls.find(tc => tc.type === 'call' && (
            tc.name === 'generate_program_portrait' ||
            tc.name === 'generate_local_image' ||
            tc.name === 'generate_imagen' ||
            tc.name === 'generate_general_image'
        ));
        if (call && call.args && call.args.prompt) {
            portraitPrompt = call.args.prompt;
        }
    }

    const row = document.createElement('div');
    row.className = `message-row ${role}-row`;
    row.dataset.role = role;
    row.dataset.rawText = text;
    
    const firstImg = (msg.media || []).find(m => m.type === 'image');
    row.dataset.imageUrl = firstImg ? firstImg.url : '';
    row.dataset.toolCalls = JSON.stringify(msg.tool_calls || []);
    row.dataset.timestamp = msg.timestamp || '';
    row.dataset.duration = msg.duration || '';
    row.dataset.msgId = msgId;
    row.dataset.contentHash = computeContentHash(msg);

    if (role === 'program') {
        const avatarContainer = document.createElement('div');
        avatarContainer.className = 'avatar-container';

        const avatar = document.createElement('img');
        avatar.className = 'avatar program-avatar';
        const profileUrl = getProfileUrl();
        avatar.src = profileUrl;
        avatar.alt = 'Program';
        avatar.title = 'Click to expand profile';
        avatar.onclick = () => expandImage(profileUrl);
        avatarContainer.appendChild(avatar);
        row.appendChild(avatarContainer);
    }

    const bubblesContainer = document.createElement('div');
    bubblesContainer.className = 'message-bubbles-container';

    const bubblesToCreate = [];
    const isTextEmpty = !text.replace(/[:\s]/g, '').trim();

    if (!isTextEmpty) {
        bubblesToCreate.push({ type: 'text', content: text });
    }
    if (msg.media) {
        msg.media.forEach(m => {
            bubblesToCreate.push({ type: 'media', content: m });
        });
    }
    if (bubblesToCreate.length === 0) {
        let fallbackText = text;
        if (!fallbackText && msg.tool_calls) {
            const skillCall = msg.tool_calls.find(tc => (tc.name === 'arena_request_skill_check' || tc.name === 'request_skill_check') && tc.args);
            if (skillCall && skillCall.args) {
                const reason = skillCall.args.reason || (skillCall.args.skill_name ? `${skillCall.args.skill_name} check required.` : '');
                if (reason) fallbackText = `*${reason}*`;
            }
        }
        bubblesToCreate.push({ type: 'text', content: fallbackText || '*(Empty message)*' });
    }

    bubblesToCreate.forEach((item, idx) => {
        const isMediaItem = item.type === 'media';
        const rawContent = (typeof item.content === 'string' ? item.content : '').trim();
        const isMarkdownImgOnly = rawContent.startsWith('![') && rawContent.endsWith(')');
        const isHtmlImgOnly = rawContent.startsWith('<img') && rawContent.endsWith('>');
        const isImageOnly = isMediaItem || isMarkdownImgOnly || isHtmlImgOnly;

        const bubble = document.createElement('div');
        bubble.className = `message ${role}` + (isImageOnly ? ' image-message' : '');
        bubble.dataset.rawText = text;
        bubble.dataset.msgId = msgId;
        if (isMsgTransient) {
            bubble.dataset.isTransient = "true";
        }

        const shouldAddStandardActions = (item.type === 'text') || (bubblesToCreate.length === 1);
        const actions = document.createElement('div');
        actions.className = 'message-actions';

        if (shouldAddStandardActions) {
            let msgTimestamp = msg.timestamp;
            if (!msgTimestamp && isLive) {
                msgTimestamp = Date.now() / 1000;
            }
            if (msgTimestamp && !isImageOnly) {
                const tsSpan = document.createElement('span');
                tsSpan.className = 'message-timestamp';
                tsSpan.textContent = formatMessageTimestamp(msgTimestamp, msg);
                actions.appendChild(tsSpan);
            }

            if (role === 'user') {
                if (!isMsgTransient && !isImageOnly && item.type === 'text') {
                    const rerollBtn = document.createElement('button');
                    rerollBtn.className = 'action-icon-btn';
                    rerollBtn.title = 'Reroll Message';
                    rerollBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
                        </svg>
                    `;
                    rerollBtn.onclick = () => rerollUserMessage(rerollBtn);
                    actions.appendChild(rerollBtn);
                }
            } else if (role === 'program' && !text.startsWith("Hello, " + getUserDisplayName())) {
                if (!isMsgTransient && !isImageOnly && item.type === 'text') {
                    const rerollBtn = document.createElement('button');
                    rerollBtn.className = 'action-icon-btn';
                    rerollBtn.title = 'Reroll response';
                    rerollBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
                        </svg>
                    `;
                    rerollBtn.onclick = () => rerollFromMessage(rerollBtn);
                    actions.appendChild(rerollBtn);

                    const speakBtn = document.createElement('button');
                    speakBtn.className = 'action-icon-btn speak-btn';
                    speakBtn.title = 'Read Message';
                    speakBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                        </svg>
                    `;
                    speakBtn.onclick = () => speakMessage(speakBtn);
                    actions.appendChild(speakBtn);
                }
            }
        }

        if (actions.children.length > 0) {
            bubble.appendChild(actions);
        }

        if (item.type === 'text') {
            let actualResponse = item.content || '';
            if (role === 'program' && actualResponse) {
                const cleaned = actualResponse.replace(/<think>[\s\S]*?<\/think>/gi, '')
                                              .replace(/\[think\][\s\S]*?\[\/think\]/gi, '')
                                              .replace(/<thought>[\s\S]*?<\/thought>/gi, '')
                                              .replace(/\[thought\][\s\S]*?\[\/thought\]/gi, '')
                                              .replace(/<\|thought\|>[\s\S]*?<\|\/thought\|>/gi, '')
                                              .replace(/<\|channel\|>[\s\S]*?<\|\/channel\|>/gi, '')
                                              .replace(/<\|channel\|>|<channel\|>/gi, '')
                                              .trim();
                actualResponse = cleaned || item.content.trim();
            }

            if (actualResponse) {
                actualResponse = actualResponse.replace(/<!--[\s\S]*?-->/g, '').trim();
                actualResponse = replacePlaceholders(actualResponse);
                const textDiv = document.createElement('div');
                textDiv.className = 'message-text';
                if (role === 'program' || role === 'user') {
                    let parsedHtml = actualResponse;
                    if (typeof marked !== 'undefined' && marked.parse) {
                        try {
                            parsedHtml = marked.parse(actualResponse);
                        } catch (me) {
                            console.error("Marked parsing error:", me);
                        }
                    }
                    textDiv.innerHTML = parsedHtml;
                    if (typeof hljs !== 'undefined' && hljs.highlightElement) {
                        textDiv.querySelectorAll('pre code').forEach((block) => {
                            try {
                                hljs.highlightElement(block);
                            } catch (he) {
                                console.error("Highlight.js error:", he);
                            }
                        });
                    }
                    postProcessMessageHTML(textDiv);
                } else {
                    textDiv.textContent = actualResponse;
                }
                bubble.appendChild(textDiv);
                if (role === 'program' && isLive) {
                    const toolCtx = (msg.tool_calls || []).map(tc => `${tc.name || ''} ${JSON.stringify(tc.args || {})}`).join(' ');
                    evaluateSceneBGM(item.content || actualResponse, toolCtx);
                }
            }

            if (msg.tool_calls && msg.tool_calls.length > 0) {
                renderCompletedLogs(bubble, msg.tool_calls, msg.duration);
            }

        } else if (item.type === 'media') {
            const mediaItem = item.content;
            const imgUrl = mediaItem.url;
            const isVideo = mediaItem.type === 'video';

            if (isVideo) {
                const videoContainer = document.createElement('div');
                videoContainer.className = 'message-video-container';
                videoContainer.style.marginTop = '8px';
                
                const video = document.createElement('video');
                video.src = imgUrl;
                video.controls = true;
                video.style.maxWidth = '100%';
                video.style.maxHeight = '300px';
                video.style.borderRadius = '12px';
                
                videoContainer.appendChild(video);
                bubble.appendChild(videoContainer);
            } else {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'message-image-container';
                
                const img = document.createElement('img');
                img.src = imgUrl;
                img.style.cursor = 'pointer';
                img.title = 'Click to expand';
                img.onclick = () => expandImage(imgUrl);
                
                if (imgUrl.includes('/images/')) {
                    const overlay = document.createElement('div');
                    overlay.className = 'image-actions-overlay';
                    
                    const editPromptBtn = document.createElement('button');
                    editPromptBtn.className = 'image-action-btn';
                    editPromptBtn.title = 'Edit prompt and regenerate';
                    editPromptBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 20h9"></path>
                            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                        </svg>
                    `;
                    editPromptBtn.onclick = async (e) => {
                        e.stopPropagation();
                        let activePrompt = mediaItem.prompt || portraitPrompt;
                        try {
                            const response = await fetch(`/api/get_image_prompt?image_url=${encodeURIComponent(img.src)}`);
                            const data = await response.json();
                            if (data.status === 'success' && data.prompt) {
                                activePrompt = data.prompt;
                            }
                        } catch (err) {
                            console.error("Failed to fetch prompt from server:", err);
                        }
                        showCustomTextareaPrompt(
                            "Edit Image Prompt",
                            "Modify the prompt to regenerate this image (Ctrl+Enter to save):",
                            activePrompt || "",
                            (newPrompt) => {
                                if (newPrompt !== null) {
                                    mediaItem.prompt = newPrompt;
                                    regenerateImage(editPromptBtn, img.src, newPrompt);
                                }
                            }
                        );
                    };
                    overlay.appendChild(editPromptBtn);

                    const recycleBtn = document.createElement('button');
                    recycleBtn.className = 'image-action-btn';
                    recycleBtn.title = 'Reroll image with the same prompt';
                    recycleBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <polyline points="1 20 1 14 7 14"></polyline>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                        </svg>
                    `;
                    recycleBtn.onclick = (e) => {
                        e.stopPropagation();
                        try {
                            regenerateImage(recycleBtn, img.src, mediaItem.prompt || portraitPrompt);
                        } catch (err) {
                            showCustomAlert("Error", "Click handler error: " + err.message);
                        }
                    };
                    overlay.appendChild(recycleBtn);

                    const animateBtn = document.createElement('button');
                    animateBtn.className = 'image-action-btn';
                    animateBtn.title = 'Animate image (video generation)';
                    animateBtn.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="23 7 16 12 23 17 23 7"></polygon>
                            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
                        </svg>
                    `;
                    animateBtn.onclick = (e) => {
                        e.stopPropagation();
                        showCustomTextareaPrompt(
                            "Animate Image",
                            "Describe the motion or animation (e.g. blinking, smiling, wind in hair, looking at camera):",
                            "gentle head turn, smiling, blinking, looking at camera",
                            (motionPrompt) => {
                                if (motionPrompt !== null) {
                                    animateImage(animateBtn, img.src, motionPrompt);
                                }
                            }
                        );
                    };
                    overlay.appendChild(animateBtn);
                    
                    imgContainer.appendChild(overlay);
                }
                
                imgContainer.appendChild(img);
                bubble.appendChild(imgContainer);
            }

            if (isTextEmpty && idx === bubblesToCreate.length - 1 && msg.tool_calls && msg.tool_calls.length > 0) {
                renderCompletedLogs(bubble, msg.tool_calls, msg.duration);
            }
        }

        bubblesContainer.appendChild(bubble);
    });

    row.appendChild(bubblesContainer);
    chatContainer.appendChild(row);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    evaluateLatestMessageForSkillCheck();

    if (role === 'program' && isLive && ttsAutoSpeak) {
        setTimeout(() => {
            const speakBtn = bubblesContainer.querySelector('.speak-btn');
            if (speakBtn) speakMessage(speakBtn);
        }, 100);
    }

    return row;
}

// --- appendMessage ---
function appendMessage(role, text, imageUrl = null, toolCalls = null, isLive = false, timestamp = null, duration = null, isTransient = false, msgId = null, vitals = null) {
    const media = [];
    if (imageUrl) {
        media.push({
            url: imageUrl,
            type: imageUrl.toLowerCase().endsWith('.mp4') ? 'video' : 'image'
        });
    }
    let cleanText = text || '';
    if (role === 'user' || role === 'program') {
        const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
        let match;
        while ((match = imgRegex.exec(cleanText)) !== null) {
            const url = match[2];
            if (!media.some(m => m.url === url)) {
                media.push({
                    url: url,
                    type: url.toLowerCase().endsWith('.mp4') ? 'video' : 'image'
                });
            }
        }
        cleanText = cleanText.replace(imgRegex, '').trim();
    }

    const activeWorldDate = currentCharacterData?.world?.date || currentCharacterData?.world?.tamrielic_date || null;
    const msg = {
        id: msgId || generateMessageId(text, role),
        role: role,
        text: cleanText,
        media: media,
        tool_calls: toolCalls,
        timestamp: timestamp,
        duration: duration,
        tamrielic_date: activeWorldDate ? JSON.parse(JSON.stringify(activeWorldDate)) : null,
        isTransient: isTransient,
        vitals: vitals,
        editable: false,
        deletable: true
    };
    return renderMessage(msg, isLive);
}

// --- postProcessMessageHTML ---
function postProcessMessageHTML(element) {
    if (!element) return;
    
    function processNode(node) {
        if (node.nodeType === Node.ELEMENT_NODE) {
            const tag = node.tagName.toLowerCase();
            if (tag === 'pre' || tag === 'code' || tag === 'a' || tag === 'textarea' || tag === 'button' || 
                node.classList.contains('thinking-block-container') || node.classList.contains('tool-logs-container')) {
                return;
            }
            const children = Array.from(node.childNodes);
            for (const child of children) {
                processNode(child);
            }
        } else if (node.nodeType === Node.TEXT_NODE) {
            const text = node.nodeValue;
            const quoteRegex = /"([^"\n]+)"|“([^”\n]+)”/g;
            if (quoteRegex.test(text)) {
                quoteRegex.lastIndex = 0;
                const tempSpan = document.createElement('span');
                const escapedText = text
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
                
                tempSpan.innerHTML = escapedText.replace(quoteRegex, (match) => {
                    return `<span class="dialogue-quote">${match}</span>`;
                });
                
                const fragment = document.createDocumentFragment();
                while (tempSpan.firstChild) {
                    fragment.appendChild(tempSpan.firstChild);
                }
                node.parentNode.replaceChild(fragment, node);
            }
        }
    }
    
    const children = Array.from(element.childNodes);
    for (const child of children) {
        processNode(child);
    }
}

/* ==========================================================================
   X. 9. CHAT TURN PROCESSING
   ========================================================================== */

// --- triggerFileInput ---
function triggerFileInput() {
    const input = document.getElementById('image-input') || imageInput;
    if (input) input.click();
}

// --- handleFileSelect ---
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const isVideo = file.type.startsWith('video/');
    const MAX_VIDEO_SIZE = 15 * 1024 * 1024; // 15MB
    if (isVideo && file.size > MAX_VIDEO_SIZE) {
        showCustomAlert("File Too Large", "Videos must be under 15MB. Please select a smaller file.");
        event.target.value = '';
        return;
    }

    previewFilename.textContent = file.name + " (uploading...)";
    previewArea.style.display = 'flex';
    
    // Hide preview elements until loaded
    previewImg.style.display = 'none';
    const previewVideo = document.getElementById('preview-video');
    if (previewVideo) previewVideo.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload_media', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || ("Upload failed: status " + response.status));
        }
        const data = await response.json();
        attachedMediaPath = data.file_path;
        attachedMime = file.type || (isVideo ? "video/mp4" : "image/jpeg");
        previewFilename.textContent = file.name + " (ready)";

        if (isVideo) {
            if (previewVideo) {
                previewVideo.src = attachedMediaPath;
                previewVideo.style.display = 'block';
            }
        } else {
            previewImg.src = attachedMediaPath;
            previewImg.style.display = 'block';
        }
    } catch (error) {
        console.error("Upload error:", error);
        previewFilename.textContent = file.name + " (upload failed)";
        showCustomAlert("Upload Error", error.message || "Failed to upload file to the server.");
        clearAttachment();
    }
}

// --- clearAttachment ---
function clearAttachment() {
    attachedBase64 = null;
    attachedMime = null;
    attachedMediaPath = null;
    const input = document.getElementById('image-input') || imageInput;
    if (input) input.value = '';
    previewArea.style.display = 'none';
    previewImg.src = '';
    previewImg.style.display = 'none';
    const previewVideo = document.getElementById('preview-video');

    if (previewVideo) {
        previewVideo.src = '';
        previewVideo.style.display = 'none';
    }
}

// --- handleSuccessReload ---
function handleSuccessReload(data) {
    const executedTools = data && data.tool_calls && data.tool_calls.length > 0;
    if (executedTools) {
        if (typeof fetchCharacterStatus === 'function') {
            fetchCharacterStatus();
        }
        const skillCheckCall = data.tool_calls.find(tc => {
            const name = tc.name || (tc.function && tc.function.name) || '';
            return name === 'arena_request_skill_check';
        });
        if (skillCheckCall) {
            let args = skillCheckCall.args || (skillCheckCall.function && skillCheckCall.function.arguments) || {};
            if (typeof args === 'string') {
                try { args = JSON.parse(args); } catch (e) { args = {}; }
            }
            activateSkillCheckUI(args);
        }
    }
}


// --- handleToolReloadOrRecovery ---
function handleToolReloadOrRecovery() {
    if (hasApprovedToolThisTurn) {
        document.getElementById('reconnect-modal').style.display = 'flex';
        let checkAttempts = 0;
        const checkInterval = setInterval(async () => {
            checkAttempts++;
            try {
                const testRes = await fetch(`/manifest.json?t=${Date.now()}`);
                if (testRes.ok) {
                    clearInterval(checkInterval);
                    document.getElementById('reconnect-modal').style.display = 'none';
                    reloadApp();
                }
            } catch (e) {
                if (checkAttempts > 20) {
                    clearInterval(checkInterval);
                    document.getElementById('reconnect-modal').style.display = 'none';
                    appendMessage('program', 'The Arena is taking a while to restart. Please refresh manually.');
                }
            }
        }, 2000);
    }
}

// --- sendMessage ---
async function sendMessage() {
    hideThoughtBubbleOverlay();
    const text = userInput.value.trim();
    if (!text && !attachedBase64 && !attachedMediaPath) {
        // Walk backwards past bottom-sentinel and transient/ghost program rows
        let lastRow = chatContainer.lastElementChild;
        while (lastRow && !lastRow.classList.contains('message-row')) {
            lastRow = lastRow.previousElementSibling;
        }
        while (lastRow && lastRow.classList.contains('program-row')) {
            const bubble = lastRow.querySelector('.message.program');
            if (bubble && bubble.dataset.isTransient === 'true') {
                lastRow = lastRow.previousElementSibling;
            } else {
                break;
            }
        }
        if (lastRow && lastRow.classList.contains('user-row')) {
            const userBubble = lastRow.querySelector('.message.user');
            if (userBubble) {
                return resendUserMessage(userBubble);
            }
        }
        return;
    }

    hasApprovedToolThisTurn = false;
    hasStagedRollMessage = false;
    setGenerating(true);
    userInput.disabled = true;
    userInput.placeholder = "";
    updateInputGlow();

    let userImageUrl = null;
    if (attachedMediaPath) {
        userImageUrl = attachedMediaPath;
    } else if (attachedBase64) {
        userImageUrl = `data:${attachedMime};base64,${attachedBase64}`;
    }
    const stagedText = text;
    const stagedBase64 = attachedBase64;
    const stagedMime = attachedMime;
    const stagedMediaPath = attachedMediaPath;

    let prefix = 'usr_';
    if (text && (text.includes("Send me a portrait of yourself") || text.includes("[GENERATE_IMAGE:") || text.includes("[GENERATE_IMAGEN:"))) {
        prefix = 'port_';
    } else if (text && text.startsWith("[SYSTEM: User has completed")) {
        prefix = 'quest_';
    } else if (text && text.startsWith("[Tool Response from")) {
        prefix = 'tool_';
    }
    const userMsgId = prefix + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    const snapshotVitals = _lastTrackedVitals.hp !== null ? {
        hp: _lastTrackedVitals.hp,
        hpMax: _lastTrackedVitals.hpMax,
        mp: _lastTrackedVitals.mp,
        mpMax: _lastTrackedVitals.mpMax,
        stamina: _lastTrackedVitals.stamina,
        staminaMax: _lastTrackedVitals.staminaMax
    } : null;
    const userMsgRow = appendMessage('user', text, userImageUrl, null, false, Date.now() / 1000, null, false, userMsgId, snapshotVitals);

    // Trigger heart jiggle on high user interaction or when Program is generating/responding
    const heartElement = document.querySelector('.heart-pulse');
    if (heartElement) {
        heartElement.classList.add('jiggling');
    }

    const payload = {
        message: text || "",
        msg_id: userMsgId,
        image_data: attachedBase64,
        image_mime: attachedMime,
        media_path: attachedMediaPath,
        session_id: sessionId,
        model: selectedModel
    };

    userInput.value = '';
    userInput.style.height = '24px';
    sessionStorage.removeItem('staged_message');
    clearAttachment();
    updateInputGlow();

    const typingIndicatorRow = document.createElement('div');
    typingIndicatorRow.className = 'message-row program-row';
    const profileUrl = getProfileUrl();
    typingIndicatorRow.innerHTML = `
        <div class="avatar-container">
            <img class="avatar program-avatar" src="${profileUrl}" alt="Program" onclick="expandImage('${profileUrl}')">
        </div>
        <div class="message program">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(typingIndicatorRow);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    startToolPolling();
    if (chatAbortController) {
        chatAbortController.abort();
    }
    chatAbortController = new AbortController();
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: chatAbortController.signal
        });
        
        chatContainer.removeChild(typingIndicatorRow);

        let data;
        try {
            data = await response.json();
        } catch (parseErr) {
            data = { error: `Server error (${response.status}): Unable to parse response.` };
        }

        if (data.cancelled) {
            return;
        }
        
        // Update user message row/bubble msgId
        const userBubbles = Array.from(chatContainer.querySelectorAll('.message.user'));
        const lastUserBubble = userBubbles[userBubbles.length - 1];
        if (lastUserBubble && data.user_msg_id) {
            lastUserBubble.dataset.msgId = data.user_msg_id;
            const row = lastUserBubble.closest('.message-row');
            if (row) {
                row.dataset.msgId = data.user_msg_id;
            }
        }
        
        if (data.response !== undefined) {
            appendMessage('program', data.response, null, data.tool_calls, true, data.timestamp, data.duration, false, data.program_msg_id);
        } else if (data.error) {
            let errMsg = data.error;
            if (errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED")) {
                errMsg = "The Arena is momentarily overwhelmed (Gemini Rate Limit 429: Resource Exhausted). Let us pause, take a slow breath, and try our chavruta again in 15 seconds.";
            }
            appendMessage('program', errMsg);
        }
        fetchCharacterStatus();
        handleSuccessReload(data);
    } catch (error) {
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        if (error.name === 'AbortError') {
            // Cancelled cleanly: user message remains in chat ready for Send/reroll
        } else {
            appendMessage('program', `*Connection error: ${error.message || 'The model was unreachable'}. Please try again.*`);
            handleToolReloadOrRecovery();
        }
    } finally {
        setGenerating(false);
        if (!activePlayerSkillCheck && !hasStagedRollMessage) {
            userInput.disabled = false;
            userInput.placeholder = "What do you do?";
            userInput.classList.remove('user-input-frozen');
            userInput.focus();
        }
        updateInputGlow();
        stopToolPolling();
        if (heartElement) {
            heartElement.classList.remove('jiggling');
        }
        await initializeModelSelect();
    }
}



// --- truncateChatAfter ---
function truncateChatAfter(row) {
    let next = row.nextElementSibling;
    while (next) {
        let toRemove = next;
        next = next.nextElementSibling;
        toRemove.remove();
    }
    evaluateLatestMessageForSkillCheck();
}

// --- startEditMessage ---
function startEditMessage(button) {
    const bubble = button.closest('.message');
    bubble.classList.add('editing');
    const container = bubble.closest('.message-bubbles-container');
    if (container) container.classList.add('editing-container');
    let textDiv = bubble.querySelector('.message-text');
    if (!textDiv) {
        textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        bubble.appendChild(textDiv);
    }
    
    const actions = bubble.querySelector('.message-actions');
    if (actions) actions.style.display = 'none';
    
    bubble.dataset.originalHTML = textDiv.innerHTML;
    
    const rawText = bubble.dataset.rawText || '';
    
    // Strip any image markdown: ![title](url)
    const imgRegex = /!\[[^\]]*\]\([^)]+\)/g;
    let strippedText = rawText.replace(imgRegex, '').trim();
    
    textDiv.innerHTML = `
        <textarea class="edit-textarea">${escapeHtml(strippedText)}</textarea>
        <div class="edit-btn-group">
            <button class="edit-btn edit-cancel-btn">Cancel</button>
            <button class="edit-btn edit-save-btn">Save</button>
        </div>
    `;
    
    const cancelBtn = textDiv.querySelector('.edit-cancel-btn');
    const saveBtn = textDiv.querySelector('.edit-save-btn');
    const textarea = textDiv.querySelector('.edit-textarea');
    
    // Auto-resize textarea to fit content
    const adjustHeight = () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    };
    adjustHeight();
    textarea.addEventListener('input', adjustHeight);
    
    textarea.focus();
    
    // Keyboard shortcuts: Ctrl+Enter / Cmd+Enter to save, Escape to cancel
    textarea.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            saveMessageEdit(bubble, textarea.value);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelMessageEdit(bubble);
        }
    });
    
    cancelBtn.onclick = (e) => {
        e.stopPropagation();
        cancelMessageEdit(bubble);
    };
    
    saveBtn.onclick = (e) => {
        e.stopPropagation();
        saveMessageEdit(bubble, textarea.value);
    };
}

// --- cancelMessageEdit ---
function cancelMessageEdit(bubble) {
    bubble.classList.remove('editing');
    const container = bubble.closest('.message-bubbles-container');
    if (container) container.classList.remove('editing-container');
    const textDiv = bubble.querySelector('.message-text');
    const actions = bubble.querySelector('.message-actions');
    if (actions) actions.style.display = '';
    
    if (bubble.dataset.originalHTML !== undefined) {
        textDiv.innerHTML = bubble.dataset.originalHTML;
    } else {
        textDiv.textContent = bubble.dataset.rawText || '';
    }
    
    delete bubble.dataset.originalHTML;
}

// --- saveMessageEdit ---
async function saveMessageEdit(bubble, newText) {
    let trimmedText = newText.trim();
    const hasImage = bubble.querySelector('img') !== null;
    
    if (!trimmedText && !hasImage) {
        showCustomAlert("Validation Error", "Cannot save an empty message.");
        return;
    }
    
    const msgId = bubble.dataset.msgId;
    if (!msgId) {
        showCustomAlert("Error", "Message ID not found.");
        return;
    }
    
    const originalRawText = bubble.dataset.rawText || '';
    const originalHTML = bubble.dataset.originalHTML || '';
    
    // Extract the original image markdown links from the original raw text
    const imgRegex = /(!\[[^\]]*\]\([^)]+\))/g;
    let imageMarkdowns = [];
    let match;
    while ((match = imgRegex.exec(originalRawText)) !== null) {
        imageMarkdowns.push(match[1]);
    }
    
    // Append them back to the new text
    let finalText = trimmedText;
    if (imageMarkdowns.length > 0) {
        if (finalText) {
            finalText += "\n\n" + imageMarkdowns.join("\n");
        } else {
            finalText = imageMarkdowns.join("\n");
        }
    }
    
    // Optimistic UI Update: Render changes instantly
    bubble.dataset.rawText = finalText;
    const row = bubble.closest('.message-row');
    if (row) {
        row.dataset.rawText = finalText;
    }
    
    const textDiv = bubble.querySelector('.message-text');
    if (trimmedText) {
        const cleanDisplay = trimmedText.replace(/<!--[\s\S]*?-->/g, '').trim();
        let parsedHtml = cleanDisplay;
        if (typeof marked !== 'undefined' && marked.parse) {
            try {
                parsedHtml = marked.parse(cleanDisplay);
            } catch (me) {
                console.error("Marked parsing error:", me);
            }
        }
        textDiv.innerHTML = parsedHtml;

        if (typeof hljs !== 'undefined' && hljs.highlightElement) {
            textDiv.querySelectorAll('pre code').forEach((block) => {
                try {
                    hljs.highlightElement(block);
                } catch (he) {
                    console.error("Highlight.js error:", he);
                }
            });
        }
        postProcessMessageHTML(textDiv);
    } else if (textDiv) {
        textDiv.remove();
    }
    
    const actions = bubble.querySelector('.message-actions');
    if (actions) actions.style.display = '';
    
    delete bubble.dataset.originalHTML;
    bubble.classList.remove('editing');
    const container = bubble.closest('.message-bubbles-container');
    if (container) container.classList.remove('editing-container');
    
    // Background server call to persist edits
    try {
        const response = await fetch('/update_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                msg_id: msgId,
                new_text: finalText
            })
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error("Background message edit failed:", error);
        showCustomAlert("Save Failed", "Could not save message edit: " + error.message);
        
        // Revert DOM to original state on failure
        bubble.dataset.rawText = originalRawText;
        if (row) {
            row.dataset.rawText = originalRawText;
        }
        
        let restoredTextDiv = bubble.querySelector('.message-text');
        if (!restoredTextDiv) {
            restoredTextDiv = document.createElement('div');
            restoredTextDiv.className = 'message-text';
            bubble.appendChild(restoredTextDiv);
        }
        restoredTextDiv.innerHTML = originalHTML;
    }
}

// --- resendUserMessage ---
async function resendUserMessage(bubble) {
    const row = bubble.closest('.message-row.user-row');
    if (!row) return;
    
    const msgId = bubble.dataset.msgId;
    if (!msgId) {
        showCustomAlert("Error", "Message ID not found.");
        return;
    }
    
    truncateChatAfter(row);
    
    hasApprovedToolThisTurn = false;
    setGenerating(true);
    const heartElement = document.querySelector('.heart-pulse');
    if (heartElement) {
        heartElement.classList.add('jiggling');
    }

    const typingIndicatorRow = document.createElement('div');
    typingIndicatorRow.className = 'message-row program-row';
    const profileUrl = getProfileUrl();
    typingIndicatorRow.innerHTML = `
        <div class="avatar-container">
            <img class="avatar program-avatar" src="${profileUrl}" alt="Program" onclick="expandImage('${profileUrl}')">
        </div>
        <div class="message program">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(typingIndicatorRow);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    userInput.disabled = true;
    userInput.placeholder = "";
    
    startToolPolling();
    if (chatAbortController) {
        chatAbortController.abort();
    }
    chatAbortController = new AbortController();
    try {
        const response = await fetch('/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                msg_id: msgId,
                new_text: bubble.dataset.rawText || '',
                model: selectedModel
            }),
            signal: chatAbortController.signal
        });
        
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        
        const data = await response.json();
        if (data.response !== undefined) {
            appendMessage('program', data.response, null, data.tool_calls, true, data.timestamp, data.duration, false, data.program_msg_id);
        } else if (data.error) {
            let errMsg = data.error;
            if (errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED")) {
                errMsg = "The Arena is momentarily overwhelmed (Gemini Rate Limit 429: Resource Exhausted). Let us pause, take a slow breath, and try our chavruta again in 15 seconds.";
            }
            appendMessage('program', errMsg);
        }
        fetchCharacterStatus();
        handleSuccessReload(data);
    } catch (error) {
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        if (error.name === 'AbortError') {
            // Cancelled cleanly
        } else {
            appendMessage('program', `*Connection error: ${error.message || 'The model was unreachable'}. Please try again.*`);
            handleToolReloadOrRecovery();
        }
    } finally {
        stopToolPolling();
        setGenerating(false);
        userInput.disabled = false;
        userInput.placeholder = "What do you do?";
        if (heartElement) {
            heartElement.classList.remove('jiggling');
        }
    }
}

// --- rerollUserMessage ---
async function rerollUserMessage(button) {
    const bubble = button.closest('.message');
    const row = bubble.closest('.message-row.user-row');
    if (!row || !bubble) return;
    
    const msgId = bubble.dataset.msgId;
    const origRawText = bubble.dataset.rawText || bubble.textContent || '';
    if (!msgId || !origRawText.trim()) return;

    const origHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `
        <div class="typing-indicator" style="padding: 0; gap: 2px; display: flex; align-items: center; justify-content: center; height: 14px;">
            <div class="typing-dot" style="width: 3px; height: 3px; background-color: var(--text-muted);"></div>
            <div class="typing-dot" style="width: 3px; height: 3px; background-color: var(--text-muted); animation-delay: -0.16s;"></div>
            <div class="typing-dot" style="width: 3px; height: 3px; background-color: var(--text-muted); animation-delay: -0.32s;"></div>
        </div>
    `;

    try {
        const genResponse = await fetch('/api/generate_user_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                model: selectedModel,
                current_input: origRawText
            })
        });

        const genData = await genResponse.json();
        if (!genData.message) {
            button.innerHTML = origHtml;
            button.disabled = false;
            if (genData.error) {
                showCustomAlert("Reroll Failed", genData.error);
            }
            return;
        }

        const newText = genData.message;
        
        // Update user bubble DOM content
        bubble.dataset.rawText = newText;
        const textElement = bubble.querySelector('.message-text');
        if (textElement) {
            textElement.innerHTML = marked.parse(newText);
            postProcessMessageHTML(textElement);
        }

        // Truncate any messages after this user turn
        truncateChatAfter(row);

        // Regenerate assistant response via /edit
        hasApprovedToolThisTurn = false;
        const heartElement = document.querySelector('.heart-pulse');
        if (heartElement) {
            heartElement.classList.add('jiggling');
        }

        const typingIndicatorRow = document.createElement('div');
        typingIndicatorRow.className = 'message-row program-row';
        const profileUrl = getProfileUrl();
        typingIndicatorRow.innerHTML = `
            <div class="avatar-container">
                <img class="avatar program-avatar" src="${profileUrl}" alt="Program" onclick="expandImage('${profileUrl}')">
            </div>
            <div class="message program">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatContainer.appendChild(typingIndicatorRow);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        userInput.disabled = true;
        userInput.placeholder = "";

        setGenerating(true);
        startToolPolling();
        if (chatAbortController) {
            chatAbortController.abort();
        }
        chatAbortController = new AbortController();

        const editResponse = await fetch('/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                msg_id: msgId,
                new_text: newText,
                model: selectedModel
            }),
            signal: chatAbortController.signal
        });

        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }

        const editData = await editResponse.json();
        if (editData.response !== undefined) {
            appendMessage('program', editData.response, null, editData.tool_calls, true, editData.timestamp, editData.duration, false, editData.program_msg_id);
        } else if (editData.error) {
            let errMsg = editData.error;
            if (errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED")) {
                errMsg = "The Arena is momentarily overwhelmed (Gemini Rate Limit 429: Resource Exhausted). Let us pause, take a slow breath, and try our chavruta again in 15 seconds.";
            }
            appendMessage('program', errMsg);
        }
        fetchCharacterStatus();
        handleSuccessReload(editData);
    } catch (error) {
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        if (error.name === 'AbortError') {
            // Cancelled cleanly
        } else {
            appendMessage('program', `*Connection error: ${error.message || 'The model was unreachable'}. Please try again.*`);
            handleToolReloadOrRecovery();
        }
    } finally {
        button.innerHTML = origHtml;
        button.disabled = false;
        stopToolPolling();
        setGenerating(false);
        userInput.disabled = false;
        userInput.placeholder = "What do you do?";
        const heartElement = document.querySelector('.heart-pulse');
        if (heartElement) {
            heartElement.classList.remove('jiggling');
        }
        await initializeModelSelect();
    }
}

// --- rerollFromMessage ---
async function rerollFromMessage(button) {
    const bubble = button.closest('.message');
    const row = bubble.closest('.message-row.program-row');
    if (!row) return;
    
    let prevRow = row.previousElementSibling;
    while (prevRow && !prevRow.classList.contains('user-row')) {
        prevRow = prevRow.previousElementSibling;
    }
    
    if (!prevRow) {
        showCustomAlert("Reroll Error", "Cannot find preceding user message to reroll.");
        return;
    }
    
    const prevBubble = prevRow.querySelector('.message.user');
    const msgId = prevBubble ? prevBubble.dataset.msgId : null;
    if (!msgId) {
        showCustomAlert("Reroll Error", "Cannot find preceding user message ID.");
        return;
    }
    
    truncateChatAfter(prevRow);
    
    hasApprovedToolThisTurn = false;
    const heartElement = document.querySelector('.heart-pulse');
    if (heartElement) {
        heartElement.classList.add('jiggling');
    }

    const typingIndicatorRow = document.createElement('div');
    typingIndicatorRow.className = 'message-row program-row';
    const profileUrl = getProfileUrl();
    typingIndicatorRow.innerHTML = `
        <div class="avatar-container">
            <img class="avatar program-avatar" src="${profileUrl}" alt="Program" onclick="expandImage('${profileUrl}')">
        </div>
        <div class="message program">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatContainer.appendChild(typingIndicatorRow);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    userInput.disabled = true;
    userInput.placeholder = "";

    setGenerating(true);
    startToolPolling();
    if (chatAbortController) {
        chatAbortController.abort();
    }
    chatAbortController = new AbortController();
    try {
        const response = await fetch('/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                msg_id: msgId,
                new_text: null,
                model: selectedModel
            }),
            signal: chatAbortController.signal
        });
        
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        
        const data = await response.json();
        if (data.response !== undefined) {
            appendMessage('program', data.response, null, data.tool_calls, true, data.timestamp, data.duration, false, data.program_msg_id);
        } else if (data.error) {
            let errMsg = data.error;
            if (errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED")) {
                errMsg = "The Arena is momentarily overwhelmed (Gemini Rate Limit 429: Resource Exhausted). Let us pause, take a slow breath, and try our chavruta again in 15 seconds.";
            }
            appendMessage('program', errMsg);
        }
        fetchCharacterStatus();
        handleSuccessReload(data);
    } catch (error) {
        if (chatContainer.contains(typingIndicatorRow)) {
            chatContainer.removeChild(typingIndicatorRow);
        }
        if (error.name === 'AbortError') {
            // Cancelled cleanly
        } else {
            appendMessage('program', `*Connection error: ${error.message || 'The model was unreachable'}. Please try again.*`);
            handleToolReloadOrRecovery();
        }
    } finally {
        stopToolPolling();
        setGenerating(false);
        userInput.disabled = false;
        userInput.placeholder = "What do you do?";
        if (heartElement) {
            heartElement.classList.remove('jiggling');
        }
        await initializeModelSelect();
    }
}

// --- deleteTurnFromMessage ---
async function deleteTurnFromMessage(button) {
    showCustomConfirm("Delete Message", "Are you sure you want to delete this message from history?", async () => {
        const bubble = button.closest('.message');
        const voiceCallRow = button.closest('.voice-call-row');
        
        if (!bubble && !voiceCallRow) return;
        
        const msgId = bubble ? bubble.dataset.msgId : (voiceCallRow ? voiceCallRow.dataset.msgId : null);

        // Truly ephemeral messages have no real server ID — remove from DOM only.
        if (bubble && bubble.dataset.isTransient === "true" && !msgId) {
            const row = bubble.closest('.message-row');
            if (row) {
                row.remove();
            }
            return;
        }

        if (!msgId) {
            showCustomAlert("Error", "Could not find message ID.");
            return;
        }
        
        try {
            const response = await fetch('/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    msg_id: msgId
                })
            });
            const data = await response.json();
            if (data.status === 'success') {
                const row = (bubble || voiceCallRow).closest('.message-row') || voiceCallRow;
                if (row) {
                    let next = row.nextElementSibling;
                    while (next) {
                        let toRemove = next;
                        next = next.nextElementSibling;
                        toRemove.remove();
                    }
                    row.remove();
                }
                evaluateLatestMessageForSkillCheck();
                if (typeof fetchCharacterStatus === 'function') {
                    fetchCharacterStatus();
                }
                if (typeof loadQuests === 'function') {
                    loadQuests();
                }

            } else if (data.error) {
                showCustomAlert("Delete Failed", data.error);
            }
        } catch (err) {
            console.error("Error deleting message:", err);
            showCustomAlert("Error", "Could not connect to the server to delete message.");
        }
    });
}

/* ==========================================================================
   XI. 10. TOOL INVOCATION & PORTRAITS
   ========================================================================== */

// --- fetchComfyCheckpoints ---
async function fetchComfyCheckpoints() {
    try {
        const select = document.getElementById('comfy-checkpoint-select');
        if (!select) return;
        
        const res = await fetch('/api/comfy/checkpoints');
        const data = await res.json();
        
        select.innerHTML = '';
        const checkpoints = data.checkpoints || [];
        if (checkpoints.length === 0) {
            const opt = document.createElement('option');
            opt.textContent = 'No checkpoints found on disk';
            select.appendChild(opt);
        } else {
            checkpoints.forEach(ckpt => {
                const opt = document.createElement('option');
                opt.value = ckpt;
                opt.textContent = ckpt;
                select.appendChild(opt);
            });
        }
        
        if (data.active) {
            select.value = data.active;
        }
    } catch (e) {
        console.error("Error fetching comfy checkpoints:", e);
    }
}

// --- changeComfyCheckpoint ---
async function changeComfyCheckpoint() {
    const select = document.getElementById('comfy-checkpoint-select');
    if (!select) return;
    
    const ckpt = select.value;
    try {
        const res = await fetch('/api/comfy/checkpoints/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ checkpoint: ckpt })
        });
        const data = await res.json();
        if (data.status === 'success') {
            // Checkpoint set successfully
        } else {
            showCustomAlert("Error", data.error || "Failed to set checkpoint");
        }
    } catch (e) {
        console.error("Error selecting comfy checkpoint:", e);
    }
}

// --- searchComfyHFCheckpoints ---
async function searchComfyHFCheckpoints() {
    const input = document.getElementById('comfy-hf-search-input');
    const resultsDiv = document.getElementById('comfy-hf-search-results');
    if (!input || !resultsDiv) return;
    
    const query = input.value.trim();
    if (!query) return;
    
    resultsDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 0.72rem;">Searching Hugging Face...</div>';
    try {
        const res = await fetch(`/api/comfy/checkpoints/search?query=${encodeURIComponent(query)}`);
        const data = await res.json();
        const results = data.results || [];
        
        if (results.length === 0) {
            resultsDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 0.72rem;">No matching checkpoints found.</div>';
            return;
        }
        
        let html = '';
        results.forEach(item => {
            html += `
                <div style="display: flex; align-items: center; justify-content: space-between; background: hsla(215, 5%, 100%, 0.03); padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-color); gap: 10px;">
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 500; font-size: 0.75rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${item.filename}">${item.filename}</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${item.repo_id}</div>
                    </div>
                    <button onclick="downloadComfyCheckpoint('${item.download_url}', '${item.filename}', this)" class="onboarding-btn" style="margin: 0; padding: 4px 8px; font-size: 0.68rem; border-radius: 4px;">Download</button>
                </div>
            `;
        });
        resultsDiv.innerHTML = html;
    } catch (e) {
        resultsDiv.innerHTML = '<div style="color: var(--danger-bright); font-size: 0.72rem;">Error searching Hugging Face.</div>';
        console.error(e);
    }
}

// --- loadServerImages ---
async function loadServerImages() {
    try {
        const response = await fetch(`/list_images?t=${Date.now()}`);
        const data = await response.json();
        if (data.images) {
            serverImages = data.images;
        }
        if (typeof pollQueueStatus === 'function') {
            pollQueueStatus();
        }
    } catch (e) {
        console.error("Error loading server images:", e);
    }
}

// --- getGalleryImages ---
function getGalleryImages() {
    const imgs = [];
    
    // Add server-side generated portraits
    serverImages.forEach(img => {
        const rel = getRelativePath(img);
        if (!rel.includes('profile.svg') && !imgs.includes(rel)) {
            imgs.push(rel);
        }
    });
    
    // Collect any additional message images and videos currently in the DOM
    const rows = document.querySelectorAll('.message-row');
    rows.forEach(row => {
        const bubble = row.querySelector('.message');
        if (bubble) {
            const messageImgs = bubble.querySelectorAll('img');
            messageImgs.forEach(img => {
                if (img.src && !img.classList.contains('avatar')) {
                    const src = img.getAttribute('src') || img.src;
                    const rel = getRelativePath(src);
                    if (!rel.includes('profile.svg') && !imgs.includes(rel)) {
                        imgs.push(rel);
                    }
                }
            });
            const messageVideos = bubble.querySelectorAll('video');
            messageVideos.forEach(vid => {
                if (vid.src) {
                    const src = vid.getAttribute('src') || vid.src;
                    const rel = getRelativePath(src);
                    if (!imgs.includes(rel)) {
                        imgs.push(rel);
                    }
                }
            });
        }
    });
    return imgs;
}

// --- expandImage ---
function expandImage(src) {
    galleryImages = getGalleryImages();
    const pathOnly = getRelativePath(src);
    
    // If the user clicked a profile avatar picture, show the first available portrait/media image
    const isProfile = pathOnly.includes('profile.png') || pathOnly.includes('profile.svg') || pathOnly.startsWith('/programs/');
    if (isProfile) {
        const profileIndex = galleryImages.findIndex(img => img.includes('profile.png'));
        if (profileIndex !== -1) {
            currentGalleryIndex = profileIndex;
        } else if (galleryImages.length === 0) {
            showCustomAlert("No Media", "No portraits or generated images exist in this arena yet.");
            return;
        } else {
            currentGalleryIndex = 0;
        }
    } else {
        currentGalleryIndex = galleryImages.indexOf(pathOnly);
        if (currentGalleryIndex === -1) {
            galleryImages.push(pathOnly);
            currentGalleryIndex = galleryImages.length - 1;
        }
    }

    document.body.style.overflow = "hidden";
    const modal = document.getElementById('image-modal');
    if (modal) modal.style.display = "flex";
    
    updateModalImage();
}

// --- updateModalImage ---
function updateModalImage() {
    const modalImg = document.getElementById('modal-img');
    const modalVideo = document.getElementById('modal-video');
    const currentSrc = galleryImages[currentGalleryIndex];
    
    const isVideo = currentSrc.toLowerCase().endsWith('.mp4') || currentSrc.toLowerCase().endsWith('.webm');
    if (isVideo) {
        if (modalImg) modalImg.style.display = 'none';
        if (modalVideo) {
            modalVideo.src = currentSrc;
            modalVideo.style.display = 'block';
        }
    } else {
        if (modalVideo) {
            modalVideo.pause();
            modalVideo.style.display = 'none';
            modalVideo.src = '';
        }
        if (modalImg) {
            modalImg.src = currentSrc;
            modalImg.style.display = 'block';
        }
    }
    
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    
    if (galleryImages.length <= 1) {
        if (prevBtn) prevBtn.style.display = 'none';
        if (nextBtn) nextBtn.style.display = 'none';
    } else {
        if (prevBtn) prevBtn.style.display = 'flex';
        if (nextBtn) nextBtn.style.display = 'flex';
    }
    
    const deleteBtn = document.getElementById('delete-gallery-btn');
    if (deleteBtn) {
        if (currentSrc.includes('profile.svg') || currentSrc.includes('profile.png')) {
            deleteBtn.style.display = 'none';
        } else {
            deleteBtn.style.display = 'flex';
        }
    }
    
    const setProfileBtn = document.getElementById('set-profile-btn');
    if (setProfileBtn) {
        if (currentSrc.includes('profile.svg') || currentSrc.includes('profile.png') || isVideo) {
            setProfileBtn.style.display = 'none';
        } else {
            setProfileBtn.style.display = 'flex';
        }
    }
}

// --- closeModal ---
function closeModal() {
    document.body.style.overflow = "";
    const modal = document.getElementById('image-modal');
    if (modal) modal.style.display = "none";
    const modalVideo = document.getElementById('modal-video');
    if (modalVideo) {
        modalVideo.pause();
        modalVideo.src = '';
    }
}

// --- prevGalleryImage ---
function prevGalleryImage(event) {
    if (event) event.stopPropagation();
    if (galleryImages.length <= 1) return;
    currentGalleryIndex = (currentGalleryIndex - 1 + galleryImages.length) % galleryImages.length;
    updateModalImage();
}

// --- nextGalleryImage ---
function nextGalleryImage(event) {
    if (event) event.stopPropagation();
    if (galleryImages.length <= 1) return;
    currentGalleryIndex = (currentGalleryIndex + 1) % galleryImages.length;
    updateModalImage();
}

// --- deleteCurrentImage ---
async function deleteCurrentImage(event) {
    if (event) event.stopPropagation();
    const currentSrc = galleryImages[currentGalleryIndex];
    if (currentSrc.includes('profile.svg') || currentSrc.includes('profile.png')) return;
    
    showCustomConfirm("Delete Image", "Are you sure you want to permanently delete this image from this conversation and the server?", async () => {
        try {
            const response = await fetch('/delete_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    image_url: currentSrc
                })
            });
            
            if (response.ok) {
                // Update DOM
                const allImgs = document.querySelectorAll('img');
                allImgs.forEach(img => {
                    if (img.id === 'modal-img') return; // Skip modal preview image to prevent UI crash
                    if (getRelativePath(img.src) === currentSrc) {
                        const parent = img.parentElement;
                        if (parent) {
                            const placeholder = document.createElement('div');
                            placeholder.className = 'deleted-image-placeholder';
                            placeholder.innerHTML = `
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; display: inline-block; vertical-align: middle;">
                                    <line x1="1" y1="1" x2="23" y2="23"></line>
                                    <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34"></path>
                                    <circle cx="12" cy="13" r="4"></circle>
                                </svg>
                                <span>[Portrait Deleted]</span>
                            `;
                            parent.replaceChild(placeholder, img);
                        }
                    }
                });
                const allVideos = document.querySelectorAll('video');
                allVideos.forEach(vid => {
                    if (vid.id === 'modal-video' || vid.id === 'preview-video') return;
                    if (getRelativePath(vid.src) === currentSrc) {
                        const container = vid.closest('.message-video-container') || vid;
                        const parent = container.parentElement;
                        if (parent) {
                            const placeholder = document.createElement('div');
                            placeholder.className = 'deleted-image-placeholder';
                            placeholder.innerHTML = `
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; display: inline-block; vertical-align: middle;">
                                    <line x1="1" y1="1" x2="23" y2="23"></line>
                                    <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34"></path>
                                    <circle cx="12" cy="13" r="4"></circle>
                                </svg>
                                <span>[Portrait Deleted]</span>
                            `;
                            parent.replaceChild(placeholder, container);
                        }
                    }
                });
                
                serverImages = serverImages.filter(img => getRelativePath(img) !== currentSrc);
                galleryImages.splice(currentGalleryIndex, 1);
                if (galleryImages.length === 0) {
                    closeModal();
                } else {
                    if (currentGalleryIndex >= galleryImages.length) {
                        currentGalleryIndex = galleryImages.length - 1;
                    }
                    updateModalImage();
                }
            } else {
                let errMsg = "Unknown error";
                try {
                    const data = await response.json();
                    errMsg = data.error || errMsg;
                } catch (e) {}
                showCustomAlert("Error Deleting Image", "Error deleting image: " + errMsg);
            }
        } catch (err) {
            console.error("Failed to delete image:", err);
            showCustomAlert("Error Deleting Image", "Failed to delete image due to network error.");
        }
    });
}

// --- deleteSpecificImage (from chat bubble action) ---
async function deleteSpecificImage(imageSrc, bubbleElement) {
    if (!imageSrc) return;
    if (imageSrc.includes('profile.svg') || imageSrc.includes('profile.png')) return;
    
    showCustomConfirm("Delete Image", "Are you sure you want to permanently delete this image from this conversation and the server?", async () => {
        try {
            const response = await fetch('/delete_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    image_url: imageSrc
                })
            });
            
            if (response.ok) {
                // Replace image with placeholder in DOM
                const allImgs = document.querySelectorAll('img');
                allImgs.forEach(img => {
                    if (img.id === 'modal-img') return;
                    if (getRelativePath(img.src) === imageSrc || img.src.includes(imageSrc)) {
                        const parent = img.parentElement;
                        if (parent) {
                            const placeholder = document.createElement('div');
                            placeholder.className = 'deleted-image-placeholder';
                            placeholder.innerHTML = `
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; display: inline-block; vertical-align: middle;">
                                    <line x1="1" y1="1" x2="23" y2="23"></line>
                                    <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34"></path>
                                    <circle cx="12" cy="13" r="4"></circle>
                                </svg>
                                <span>[Portrait Deleted]</span>
                            `;
                            parent.replaceChild(placeholder, img);
                        }
                    }
                });
                
                // Hide actions on deleted image bubble
                if (bubbleElement) {
                    const act = bubbleElement.querySelector('.message-actions');
                    if (act) act.style.display = 'none';
                }
            } else {
                let errMsg = "Unknown error";
                try {
                    const data = await response.json();
                    errMsg = data.error || errMsg;
                } catch (e) {}
                showCustomAlert("Error Deleting Image", "Error deleting image: " + errMsg);
            }
        } catch (err) {
            console.error("Failed to delete image:", err);
            showCustomAlert("Error Deleting Image", "Failed to delete image due to network error.");
        }
    });
}

// --- Circular Profile Cropping Functions ---
let profileCropper = null;
let cropSourcePath = '';

function setCurrentImageAsProfile(event) {
    if (event) event.stopPropagation();
    const currentSrc = galleryImages[currentGalleryIndex];
    if (currentSrc.includes('profile.png') || currentSrc.includes('profile.svg')) return;

    closeModal();
    cropSourcePath = currentSrc;

    const cropModal = document.getElementById('crop-modal');
    const cropImg = document.getElementById('crop-image-element');
    
    if (cropModal && cropImg) {
        if (profileCropper) {
            profileCropper.destroy();
            profileCropper = null;
        }

        cropModal.style.display = 'flex';
        
        const initCropper = () => {
            const container = document.getElementById('crop-container');
            if (container && cropImg.naturalWidth && cropImg.naturalHeight) {
                const aspect = cropImg.naturalWidth / cropImg.naturalHeight;
                const padding = window.innerWidth <= 768 ? 40 : 60;
                const availWidth = cropModal.querySelector('.modal-card').clientWidth - padding;
                const availHeight = window.innerHeight * 0.5;
                
                let finalWidth = availWidth;
                let finalHeight = finalWidth / aspect;
                
                if (finalHeight > availHeight) {
                    finalHeight = availHeight;
                    finalWidth = finalHeight * aspect;
                }
                
                container.style.width = `${finalWidth}px`;
                container.style.height = `${finalHeight}px`;
            }
            setTimeout(() => {
                if (profileCropper) {
                    profileCropper.destroy();
                }
                profileCropper = new Cropper(cropImg, {
                    aspectRatio: 1,
                    viewMode: 1,
                    dragMode: 'move',
                    autoCropArea: 0.8,
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: true,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                    checkCrossOrigin: false,
                    background: false,
                    ready() {
                        const canvasData = profileCropper.getCanvasData();
                        const size = Math.min(canvasData.width, canvasData.height) * 0.8;
                        profileCropper.setCropBoxData({
                            left: canvasData.left + (canvasData.width - size) / 2,
                            top: canvasData.top + (canvasData.height - size) / 2,
                            width: size,
                            height: size
                        });
                    }
                });
            }, 100);
        };

        cropImg.onload = function() {
            initCropper();
            cropImg.onload = null;
        };
        cropImg.src = currentSrc;

        if (cropImg.complete && cropImg.naturalWidth !== 0) {
            initCropper();
            cropImg.onload = null;
        }
    }
}

function closeCropModal(event) {
    if (event) event.stopPropagation();
    const cropModal = document.getElementById('crop-modal');
    if (cropModal) {
        cropModal.style.display = 'none';
    }
    if (profileCropper) {
        profileCropper.destroy();
        profileCropper = null;
    }
    const container = document.getElementById('crop-container');
    if (container) {
        container.style.width = '';
        container.style.height = '';
    }
}

async function saveCroppedProfile(event) {
    if (event) event.stopPropagation();
    if (!profileCropper || !cropSourcePath) return;

    // Send crop coordinates to the server — PIL handles the actual pixel cropping.
    // This eliminates all browser canvas compatibility issues.
    const cropData = profileCropper.getData(true);
    closeCropModal();
    
    try {
        const response = await fetch('/api/programs/profile_picture/crop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_image: cropSourcePath,
                x: cropData.x,
                y: cropData.y,
                width: cropData.width,
                height: cropData.height
            })
        });
        
        if (response.ok) {
            profileCacheBuster = Date.now();
            updateProfileImages();
            document.querySelectorAll('.program-list-avatar').forEach(img => {
                const originalSrc = img.tagName === 'DIV' ? img.getAttribute('src') : img.src;
                if (originalSrc) {
                    const newSrc = originalSrc.split('?')[0] + `?t=${profileCacheBuster}`;
                    updateAvatarElement(img, newSrc);
                }
            });
        } else {
            const err = await response.json();
            showCustomAlert("Error", err.error || "Failed to save profile picture.");
        }
    } catch (e) {
        console.error("Error saving cropped profile picture:", e);
        showCustomAlert("Error", "An error occurred while saving the profile picture.");
    }
}

// --- handleTouchStart ---
function handleTouchStart(event) {
    touchStartX = event.changedTouches[0].screenX;
}

// --- handleTouchEnd ---
function handleTouchEnd(event) {
    touchEndX = event.changedTouches[0].screenX;
    handleSwipeGesture();
}

// --- handleSwipeGesture ---
function handleSwipeGesture() {
    const swipeThreshold = 50;
    if (touchEndX < touchStartX - swipeThreshold) {
        nextGalleryImage();
    } else if (touchEndX > touchStartX + swipeThreshold) {
        prevGalleryImage();
    }
}

// --- generatePortraitPrompt ---
async function generatePortraitPrompt() {
    if (isGenerating) return;
    if (useImagenMode) {
        userInput.value = "[GENERATE_IMAGEN: Render an image of the active companion using Google Imagen. Do not narrate new story events or call mechanics tools.]";
    } else {
        userInput.value = "[GENERATE_IMAGE: Render an image of the active companion. Do not narrate new story events or call mechanics tools.]";
    }
    await sendMessage();
}

// --- autoGenerateUserMessage ---
async function autoGenerateUserMessage() {
    const btn = document.getElementById('auto-generate-user-btn');
    if (!btn || btn.disabled) return;
    
    const currentInput = userInput ? userInput.value : '';

    btn.disabled = true;
    btn.style.opacity = '0.5';
    btn.title = "Generating impersonated message...";
    
    userInput.disabled = true;
    userInput.placeholder = "";
    
    const origIcon = btn.innerHTML;
    btn.innerHTML = `
        <div class="typing-indicator" style="padding: 0; gap: 3px; display: flex; align-items: center; justify-content: center;">
            <div class="typing-dot" style="width: 4px; height: 4px; background-color: var(--text-muted);"></div>
            <div class="typing-dot" style="width: 4px; height: 4px; background-color: var(--text-muted); animation-delay: -0.16s;"></div>
            <div class="typing-dot" style="width: 4px; height: 4px; background-color: var(--text-muted); animation-delay: -0.32s;"></div>
        </div>
    `;
    
    try {
        const response = await fetch('/api/generate_user_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                model: selectedModel,
                current_input: currentInput
            })
        });
        
        const data = await response.json();
        if (data.message) {
            userInput.value = data.message;
            // Auto-resize textarea
            userInput.style.height = 'auto';
            userInput.style.height = (userInput.scrollHeight) + 'px';
            userInput.focus();
            updateInputGlow();
        } else if (data.error) {
            showCustomAlert("Generation Failed", data.error);
        }
    } catch (err) {
        console.error("Error auto-generating user message:", err);
        showCustomAlert("Error", "Could not connect to the server to generate message.");
    } finally {
        btn.disabled = false;
        btn.style.opacity = '0.5';
        btn.title = "Impersonate";
        btn.innerHTML = origIcon;
        userInput.disabled = false;
        userInput.placeholder = "What do you do?";
    }
}

// --- Player Skill Check System ---
let activePlayerSkillCheck = null;
let hasStagedRollMessage = false;

function activateSkillCheckUI(checkData) {
    if (!checkData || hasStagedRollMessage) return;
    activePlayerSkillCheck = checkData;

    const diceBtn = document.getElementById('dice-skill-btn');
    if (diceBtn) {
        diceBtn.classList.add('skill-check-active');
        diceBtn.title = "Skill Check";
    }

    if (userInput) {
        userInput.disabled = true;
        userInput.placeholder = `${checkData.skill_name || 'Action'} (DC ${checkData.dc || 15})`;
        userInput.classList.add('user-input-frozen');
    }

    const autoGenBtn = document.getElementById('auto-generate-user-btn');
    if (autoGenBtn) {
        autoGenBtn.disabled = true;
        autoGenBtn.style.opacity = '0.25';
        autoGenBtn.style.pointerEvents = 'none';
    }

    const portraitBtn = document.getElementById('generate-portrait-btn');
    if (portraitBtn) {
        portraitBtn.disabled = true;
        portraitBtn.style.opacity = '0.25';
        portraitBtn.style.pointerEvents = 'none';
    }

    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.style.opacity = '0.25';
        sendBtn.style.pointerEvents = 'none';
    }
}

function evaluateLatestMessageForSkillCheck() {
    if (hasStagedRollMessage) return;
    if (!chatContainer) return;
    const allRows = Array.from(chatContainer.querySelectorAll('.message-row:not(#welcome-message):not(#onboarding-container)'));
    if (allRows.length === 0) {
        resetSkillCheckUI();
        return;
    }
    
    const lastRow = allRows[allRows.length - 1];
    if (!lastRow || !lastRow.classList.contains('program-row')) {
        resetSkillCheckUI();
        return;
    }

    const toolCallsStr = lastRow.dataset.toolCalls;
    if (toolCallsStr) {
        try {
            const toolCalls = JSON.parse(toolCallsStr);
            const skillCheckCall = toolCalls.find(tc => {
                const name = tc.name || (tc.function && tc.function.name) || '';
                return name === 'arena_request_skill_check';
            });
            if (skillCheckCall) {
                let args = skillCheckCall.args || (skillCheckCall.function && skillCheckCall.function.arguments) || {};
                if (typeof args === 'string') {
                    try { args = JSON.parse(args); } catch (e) { args = {}; }
                }
                activateSkillCheckUI(args);
                return;
            }
        } catch (e) {}
    }
    
    resetSkillCheckUI();
}

function resetSkillCheckUI() {
    activePlayerSkillCheck = null;
    hasStagedRollMessage = false;

    const diceBtn = document.getElementById('dice-skill-btn');
    if (diceBtn) {
        diceBtn.classList.remove('skill-check-active');
        diceBtn.classList.remove('rolling');
        diceBtn.disabled = false;
        diceBtn.style.opacity = '';
        diceBtn.style.pointerEvents = '';
        diceBtn.title = "Skill Check";
    }

    if (userInput) {
        userInput.disabled = false;
        userInput.placeholder = "What do you do?";
        userInput.classList.remove('user-input-frozen');
    }

    const autoGenBtn = document.getElementById('auto-generate-user-btn');
    if (autoGenBtn) {
        autoGenBtn.disabled = false;
        autoGenBtn.style.opacity = '';
        autoGenBtn.style.pointerEvents = '';
    }

    const portraitBtn = document.getElementById('generate-portrait-btn');
    if (portraitBtn) {
        portraitBtn.disabled = false;
        portraitBtn.style.opacity = '';
        portraitBtn.style.pointerEvents = '';
    }

    const imgUploadBtn = document.getElementById('image-upload-btn');
    if (imgUploadBtn) {
        imgUploadBtn.disabled = false;
        imgUploadBtn.style.opacity = '';
        imgUploadBtn.style.pointerEvents = '';
    }

    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.style.opacity = '';
        sendBtn.style.pointerEvents = '';
    }
}

function getDiceIconSvg() {
    return `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="4" ry="4"></rect>
            <circle cx="8" cy="8" r="1.2" fill="currentColor"></circle>
            <circle cx="16" cy="8" r="1.2" fill="currentColor"></circle>
            <circle cx="12" cy="12" r="1.2" fill="currentColor"></circle>
            <circle cx="8" cy="16" r="1.2" fill="currentColor"></circle>
            <circle cx="16" cy="16" r="1.2" fill="currentColor"></circle>
        </svg>
    `;
}

async function handleDiceButtonClick() {
    const diceBtn = document.getElementById('dice-skill-btn');
    if (!diceBtn || isGenerating || hasStagedRollMessage || diceBtn.disabled) {
        return;
    }
    await resolvePlayerSkillCheck();
}

async function resolvePlayerSkillCheck() {
    const checkData = activePlayerSkillCheck ? { ...activePlayerSkillCheck } : null;
    const isFlat = !checkData;
    const diceBtn = document.getElementById('dice-skill-btn');

    if (diceBtn) {
        diceBtn.classList.remove('skill-check-active');
        diceBtn.classList.add('rolling');
        diceBtn.innerHTML = getDiceIconSvg();
    }

    try {
        const payload = isFlat ? {
            session_id: sessionId,
            model: selectedModel,
            is_flat_roll: true
        } : {
            session_id: sessionId,
            skill_name: checkData.skill_name || 'Agility',
            attribute_name: checkData.attribute_name || 'Agility',
            dc: checkData.dc || 15,
            reason: checkData.reason || '',
            model: selectedModel,
            is_flat_roll: false
        };

        const response = await fetch('/api/execute_player_skill_check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.formatted_message) {
            userInput.value = data.formatted_message;
            userInput.style.height = 'auto';
            userInput.style.height = (userInput.scrollHeight) + 'px';

            // Keep text area locked until pressing send so player cannot edit roll result before sending
            userInput.disabled = true;
            userInput.classList.add('user-input-frozen');
            userInput.placeholder = "Roll action generated — Click Send to submit";

            // Lock dice button so player cannot reroll outcome before sending
            if (diceBtn) {
                diceBtn.classList.remove('skill-check-active');
                diceBtn.classList.remove('rolling');
                diceBtn.disabled = true;
                diceBtn.style.opacity = '0.25';
                diceBtn.style.pointerEvents = 'none';
                diceBtn.title = "Roll locked — Send action to submit";
            }

            // Keep toolbar buttons disabled while staged roll message is locked
            const autoGenBtn = document.getElementById('auto-generate-user-btn');
            if (autoGenBtn) {
                autoGenBtn.disabled = true;
                autoGenBtn.style.opacity = '0.25';
                autoGenBtn.style.pointerEvents = 'none';
            }

            const portraitBtn = document.getElementById('generate-portrait-btn');
            if (portraitBtn) {
                portraitBtn.disabled = true;
                portraitBtn.style.opacity = '0.25';
                portraitBtn.style.pointerEvents = 'none';
            }

            const imgUploadBtn = document.getElementById('image-upload-btn');
            if (imgUploadBtn) {
                imgUploadBtn.disabled = true;
                imgUploadBtn.style.opacity = '0.25';
                imgUploadBtn.style.pointerEvents = 'none';
            }

            // Unlock and focus the send button so the user can send with one click or Enter
            const sendBtn = document.querySelector('.send-btn');
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.style.opacity = '';
                sendBtn.style.pointerEvents = '';
                sendBtn.focus();
            }

            hasStagedRollMessage = true;
            activePlayerSkillCheck = null;
            updateInputGlow();

        } else if (data.error) {
            showCustomAlert("Skill Check Failed", data.error);
            resetSkillCheckUI();
        }
    } catch (err) {
        console.error("Error executing player skill check:", err);
        showCustomAlert("Error", "Could not execute skill check.");
        resetSkillCheckUI();
    } finally {
        if (diceBtn && !hasStagedRollMessage) {
            diceBtn.classList.remove('rolling');
        }
    }
}





// --- regenerateImage ---
async function regenerateImage(buttonElement, oldImageUrl, prompt) {

    try {
        const container = buttonElement.closest('.message-image-container');
        if (!container) {
            showCustomAlert("Reroll Failed", "Reroll failed: message-image-container parent not found!");
            return;
        }
        const img = container.querySelector('img');
        if (!img) {
            showCustomAlert("Reroll Failed", "Reroll failed: img tag inside container not found!");
            return;
        }
        
        // Create loading overlay
        let overlay = container.querySelector('.image-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'image-loading-overlay';
            overlay.innerHTML = `
                <div class="typing-indicator" style="gap: 6px;">
                    <div class="typing-dot" style="background-color: var(--primary-accent);"></div>
                    <div class="typing-dot" style="background-color: var(--primary-accent); animation-delay: -0.16s;"></div>
                    <div class="typing-dot" style="background-color: var(--primary-accent); animation-delay: -0.32s;"></div>
                </div>
            `;
            container.appendChild(overlay);
        }
        buttonElement.style.pointerEvents = 'none';
        buttonElement.style.opacity = '0.5';

        startToolPolling();
        
        const response = await fetch('/regenerate_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                old_image_url: getRelativePath(oldImageUrl),
                prompt: prompt,
                use_imagen: useImagenMode
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            img.src = data.new_image_url;
            img.onclick = () => expandImage(data.new_image_url);
            await loadServerImages();

            // Re-render Activity Log in completed ("Ran...") state
            try {
                const bubble = buttonElement.closest('.message.program');
                if (bubble) {
                    const logRes = await fetch(`/api/session_tool_calls?session_id=${sessionId}`);
                    const logData = await logRes.json();
                    if (logData.tool_calls && logData.tool_calls.length > 0) {
                        // Convert Python session tool calls to Gemini type/format
                        const geminiToolCalls = [];
                        logData.tool_calls.forEach(tc => {
                            geminiToolCalls.push({
                                type: 'call',
                                name: tc.name,
                                args: tc.args ? { prompt: tc.args } : {},
                                id: tc.id
                            });
                            geminiToolCalls.push({
                                type: 'response',
                                name: tc.name,
                                response: tc.response || '',
                                id: tc.id
                            });
                        });
                        const totalDur = logData.tool_calls.reduce((sum, tc) => sum + (tc.duration || 0), 0);
                        renderCompletedLogs(bubble, geminiToolCalls, totalDur ? Math.round(totalDur * 10) / 10 : null);
                    }
                }
            } catch (err) {
                console.error("Error finalizing activity logs after reroll:", err);
            }
        } else {
            let errorMsg = data.error || 'Unknown error';
            if (typeof marked !== 'undefined' && marked.parse) {
                try {
                    errorMsg = marked.parse(errorMsg);
                } catch (me) {
                    console.error("Marked parsing error in error alert:", me);
                }
            }
            showCustomAlert("Image Regeneration Failed", errorMsg);
        }
    } catch (error) {
        console.error("Error regenerating image:", error);
        showCustomAlert("Connection Error", "Failed to connect to the server for image regeneration: " + error.message);
    } finally {
        const container = buttonElement.closest('.message-image-container');
        if (container) {
            const overlay = container.querySelector('.image-loading-overlay');
            if (overlay) overlay.remove();
        }
        buttonElement.style.pointerEvents = 'auto';
        buttonElement.style.opacity = '';
        stopToolPolling();
        await initializeModelSelect();
    }
}


let activeQueueTasks = {};
let queuePollInterval = null;

function startQueuePolling() {
    if (queuePollInterval) return;
    pollQueueStatus();
    queuePollInterval = setInterval(pollQueueStatus, 15000);
}

function stopQueuePolling() {
    if (queuePollInterval) {
        clearInterval(queuePollInterval);
        queuePollInterval = null;
    }
}

function findChatImageByUrl(url) {
    const relUrl = getRelativePath(url);
    const imgs = document.querySelectorAll('.message-image-container img');
    for (let img of imgs) {
        if (getRelativePath(img.src) === relUrl) {
            return img;
        }
    }
    return null;
}

function showImageLoadingOverlay(container, status) {
    let overlay = container.querySelector('.image-loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'image-loading-overlay';
        container.appendChild(overlay);
    }
    const label = status === 'queued' ? 'Queued...' : 'Generating Video...';
    overlay.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--primary-accent);">
            <div class="typing-indicator" style="gap: 6px;">
                <div class="typing-dot" style="background-color: var(--primary-accent);"></div>
                <div class="typing-dot" style="background-color: var(--primary-accent); animation-delay: -0.16s;"></div>
                <div class="typing-dot" style="background-color: var(--primary-accent); animation-delay: -0.32s;"></div>
            </div>
            <span style="font-size: 0.75rem; font-weight: 500; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">${label}</span>
        </div>
    `;
    
    // Disable action buttons in the overlay
    const overlayBtns = container.querySelectorAll('.image-action-btn');
    overlayBtns.forEach(btn => {
        btn.style.pointerEvents = 'none';
        btn.style.opacity = '0.5';
    });
}

function updateImageLoadingText(container, status) {
    const span = container.querySelector('.image-loading-overlay span');
    if (span) {
        span.textContent = status === 'queued' ? 'Queued...' : 'Generating Video...';
    }
}

function showImageErrorOverlay(container, error) {
    const overlay = container.querySelector('.image-loading-overlay');
    if (overlay) {
        overlay.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--danger-vivid); padding: 10px; text-align: center;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span style="font-size: 0.75rem; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">Generation Failed</span>
                <button class="icon-btn" onclick="this.closest('.image-loading-overlay').remove();" style="font-size: 0.7rem; padding: 2px 8px; background: hsla(215, 5%, 100%, 0.1); border-radius: 4px; margin-top: 4px; color: var(--text-bright); cursor: pointer; pointer-events: auto;">Dismiss</button>
            </div>
        `;
    }
    
    // Re-enable action buttons
    const overlayBtns = container.querySelectorAll('.image-action-btn');
    overlayBtns.forEach(btn => {
        btn.style.pointerEvents = 'auto';
        btn.style.opacity = '';
    });
}

function swapImageWithVideo(container, videoUrl) {
    const bubble = container.closest('.message.program');
    if (bubble) {
        container.remove();
        
        const videoContainer = document.createElement('div');
        videoContainer.className = 'message-video-container';
        videoContainer.style.marginTop = '8px';
        
        const video = document.createElement('video');
        video.src = videoUrl;
        video.controls = true;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.style.maxWidth = '100%';
        video.style.maxHeight = '300px';
        video.style.borderRadius = '12px';
        
        videoContainer.appendChild(video);
        
        const textDiv = bubble.querySelector('.message-text');
        if (textDiv) {
            bubble.insertBefore(videoContainer, textDiv);
        } else {
            bubble.appendChild(videoContainer);
        }
    }
}

function updateQueueModalUI(generations) {
    const queueContainer = document.getElementById('gallery-queue-container');
    const queueListItems = document.getElementById('queue-list-items');
    const badge = document.getElementById('queue-count-badge');
    
    if (!queueContainer || !queueListItems) return;
    
    const activeTasks = generations.filter(g => g.status === 'queued' || g.status === 'generating');
    
    if (activeTasks.length === 0) {
        queueContainer.style.display = 'none';
        return;
    }
    
    queueContainer.style.display = 'block';
    if (badge) badge.textContent = activeTasks.length;
    
    queueListItems.innerHTML = '';
    activeTasks.forEach(task => {
        const item = document.createElement('div');
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.gap = '10px';
        item.style.padding = '8px';
        item.style.background = 'hsla(215, 5%, 100%, 0.04)';
        item.style.borderRadius = '8px';
        item.style.border = '1px solid hsla(215, 5%, 100%, 0.05)';
        
        const statusLabel = task.status === 'queued' ? 'Queued' : 'Rendering';
        
        item.innerHTML = `
            <img src="${task.source_image}" style="width: 36px; height: 36px; border-radius: 6px; object-fit: cover; border: 1px solid hsla(215, 5%, 100%, 0.1);">
            <div style="flex-grow: 1; min-width: 0;">
                <div style="font-weight: 600; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${task.prompt}</div>
                <div style="font-size: 0.7rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
                    <span class="typing-dot" style="background: var(--primary-accent); width: 6px; height: 6px; border-radius: 50%; display: inline-block;"></span>
                    <span>${statusLabel}</span>
                </div>
            </div>
        `;
        queueListItems.appendChild(item);
    });
}

async function pollQueueStatus() {
    try {
        const response = await fetch(`/api/generations?t=${Date.now()}`);
        if (!response.ok) return;
        
        const data = await response.json();
        if (!data.generations) return;
        
        updateQueueModalUI(data.generations);
        
        let activeTaskIds = Object.keys(activeQueueTasks);
        if (activeTaskIds.length === 0) {
            data.generations.forEach(gen => {
                if (gen.status === 'queued' || gen.status === 'generating') {
                    const img = findChatImageByUrl(gen.source_image);
                    if (img) {
                        const container = img.closest('.message-image-container');
                        if (container) {
                            container.setAttribute('data-task-id', gen.task_id);
                            showImageLoadingOverlay(container, gen.status);
                            activeQueueTasks[gen.task_id] = {
                                task_id: gen.task_id,
                                source_image: gen.source_image,
                                container: container
                            };
                        }
                    }
                }
            });
            activeTaskIds = Object.keys(activeQueueTasks);
            if (activeTaskIds.length === 0) {
                stopQueuePolling();
                return;
            }
        }
        
        data.generations.forEach(gen => {
            const task = activeQueueTasks[gen.task_id];
            if (task) {
                if (gen.status === 'completed') {
                    swapImageWithVideo(task.container, gen.result_url);
                    delete activeQueueTasks[gen.task_id];
                } else if (gen.status === 'failed') {
                    showImageErrorOverlay(task.container, gen.error);
                    delete activeQueueTasks[gen.task_id];
                } else {
                    updateImageLoadingText(task.container, gen.status);
                }
            }
        });
        
        if (Object.keys(activeQueueTasks).length === 0) {
            stopQueuePolling();
            loadServerImages();
        }
    } catch (e) {
        console.error("Error polling queue status:", e);
    }
}

// --- animateImage ---
async function animateImage(buttonElement, oldImageUrl, motionPrompt) {

    try {
        const container = buttonElement.closest('.message-image-container');
        if (!container) {
            showCustomAlert("Animation Failed", "Animation failed: message-image-container parent not found!");
            return;
        }
        const img = container.querySelector('img');
        if (!img) {
            showCustomAlert("Animation Failed", "Animation failed: img tag inside container not found!");
            return;
        }
        
        showImageLoadingOverlay(container, 'queued');
        buttonElement.style.pointerEvents = 'none';
        buttonElement.style.opacity = '0.5';
        
        const response = await fetch('/api/animate_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                image_url: getRelativePath(oldImageUrl),
                prompt: motionPrompt
            })
        });
        
        const data = await response.json();
        if (response.ok && data.status === 'queued') {
            container.setAttribute('data-task-id', data.task_id);
            activeQueueTasks[data.task_id] = {
                task_id: data.task_id,
                source_image: oldImageUrl,
                container: container
            };
            startQueuePolling();
        } else {
            let errorMsg = data.error || 'Unknown error';
            if (typeof marked !== 'undefined' && marked.parse) {
                try {
                    errorMsg = marked.parse(errorMsg);
                } catch (me) {
                    console.error("Marked parsing error in error alert:", me);
                }
            }
            showImageErrorOverlay(container, errorMsg);
        }
    } catch (error) {
        console.error("Error animating image:", error);
        const container = buttonElement.closest('.message-image-container');
        if (container) {
            showImageErrorOverlay(container, "Failed to connect to the server: " + error.message);
        }
    } finally {
        buttonElement.style.pointerEvents = 'auto';
        buttonElement.style.opacity = '';
        await initializeModelSelect();
    }
}





// --- startToolPolling ---
function startToolPolling() {
    if (toolPollInterval) clearInterval(toolPollInterval);
    let lastActiveToolsStr = "";
    
    const pollFunc = async () => {
        try {
            const response = await fetch('/pending_tool_call');
            const data = await response.json();
            
            // Update activity exclamation badge on the avatar if typing indicator exists
            const typingIndicator = document.querySelector('.typing-indicator');
            if (typingIndicator) {
                const row = typingIndicator.closest('.program-row');
                if (row) {
                    const avatarContainer = row.querySelector('.avatar-container');
                    if (avatarContainer) {
                        let excl = avatarContainer.querySelector('.activity-exclamation');
                        const currentToolsStr = (data.active_tools || []).join(',');
                        
                        if (data.active_tools && data.active_tools.length > 0) {
                            const isNewCall = currentToolsStr !== lastActiveToolsStr;
                            lastActiveToolsStr = currentToolsStr;
                            
                            if (!excl) {
                                excl = document.createElement('div');
                                excl.className = 'activity-exclamation';
                                excl.textContent = '!';
                                avatarContainer.appendChild(excl);
                            } else if (isNewCall) {
                                // Reset CSS animation to trigger the quick-ping effect again
                                excl.style.animation = 'none';
                                excl.offsetHeight; // trigger reflow
                                excl.style.animation = '';
                            }
                            excl.style.display = 'flex';
                            const toolsNames = data.active_tools.map(t => {
                                return t.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
                            }).join(', ');
                            excl.title = `Running: ${toolsNames}`;
                        } else {
                            lastActiveToolsStr = "";
                            if (excl) {
                                excl.remove();
                            }
                        }
                    }
                }
                
                const bubble = typingIndicator.closest('.message.program');
                if (bubble) {
                    try {
                        const logRes = await fetch(`/api/session_tool_calls?session_id=${sessionId}`);
                        const logData = await logRes.json();
                        if (logData.tool_calls && logData.tool_calls.length > 0) {
                            updateLiveLogs(bubble, logData.tool_calls);
                        }
                    } catch (e) {
                        console.error("Error polling session tool calls:", e);
                    }
                }
            }
            
            if (data.call_id && toolPollInterval) {
                clearInterval(toolPollInterval); // Pause polling while showing modal
                toolPollInterval = null;
                showToolConfirmModal(data.call_id, data.tool_name, data.details);
            }
        } catch (e) {
            console.error("Error polling for tool calls:", e);
        }
    };
    
    pollFunc(); // Poll immediately
    toolPollInterval = setInterval(pollFunc, 4000);
}

function updateLiveLogs(bubble, toolCalls) {
    if (!toolCalls || toolCalls.length === 0) return;
    
    let logsContainer = bubble.querySelector('.antigravity-logs-container');
    if (!logsContainer) {
        logsContainer = document.createElement('div');
        logsContainer.className = 'antigravity-logs-container';
        bubble.appendChild(logsContainer);
    }
    
    let logsCard = logsContainer.querySelector('.antigravity-logs-card');
    if (!logsCard) {
        logsCard = document.createElement('div');
        logsCard.className = 'antigravity-logs-card';
        logsContainer.appendChild(logsCard);
    }
    
    let header = logsCard.querySelector('.antigravity-logs-header');
    if (!header) {
        header = document.createElement('div');
        header.className = 'antigravity-logs-header';
        header.innerHTML = `
            <span class="ag-timer-icon">${getLogIconSvg('timer')}</span>
            <span class="ag-timer-text">Working...</span>
            <span class="ag-header-chevron">▼</span>
        `;
        logsCard.appendChild(header);
        
        header.onclick = (e) => {
            e.stopPropagation();
            const body = logsCard.querySelector('.antigravity-logs-body');
            if (body) {
                const isExpanded = body.style.display === 'flex' || body.style.display === 'block';
                body.style.display = isExpanded ? 'none' : 'flex';
                header.querySelector('.ag-header-chevron').classList.toggle('expanded', !isExpanded);
            }
        };
    }
    
    let body = logsCard.querySelector('.antigravity-logs-body');
    if (!body) {
        body = document.createElement('div');
        body.className = 'antigravity-logs-body';
        body.style.display = 'none'; // Collapsed by default during live generation
        logsCard.appendChild(body);
    }
    
    body.innerHTML = '';
    
    toolCalls.forEach(tc => {
        const itemEl = document.createElement('div');
        itemEl.className = 'antigravity-log-item';
        
        let icon = getLogIconSvg('gear');
        let action = 'Running';
        let target = tc.name;
        
        if (tc.status === 'completed') {
            action = 'Completed';
        } else if (tc.status === 'failed') {
            action = 'Failed';
        }
        
        const name = tc.name;
        if (name.includes('search')) {
            icon = getLogIconSvg('search');
            action = tc.status === 'running' ? 'Searching' : (tc.status === 'completed' ? 'Searched' : 'Search failed');
        } else if (name.includes('read_file') || name.includes('view_file')) {
            icon = getLogIconSvg('file');
            action = tc.status === 'running' ? 'Reading' : (tc.status === 'completed' ? 'Read' : 'Read failed');
        } else if (name.includes('write_file') || name.includes('replace') || name.includes('edit')) {
            icon = getLogIconSvg('edit');
            action = tc.status === 'running' ? 'Writing' : (tc.status === 'completed' ? 'Wrote' : 'Write failed');
        } else if (name.includes('command') || name.includes('shell')) {
            icon = getLogIconSvg('command');
            action = tc.status === 'running' ? 'Running' : (tc.status === 'completed' ? 'Ran' : 'Execution failed');
        }
        
        target = tc.args || '';
        if (target.length > 50) {
            target = target.substring(0, 47) + '...';
        }
        
        let durText = tc.duration ? ` (${tc.duration}s)` : '';
        itemEl.innerHTML = `
            <span class="ag-log-icon">${icon}</span>
            <span class="ag-log-action" style="font-weight: 500;">${action}</span>
            <span class="ag-log-target" style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted); opacity: 0.85; margin-left: 4px;">${tc.name}(${target})</span>
            <span class="ag-log-suffix" style="margin-left: auto; font-size: 0.7rem; color: var(--text-muted);">${durText}</span>
        `;
        
        const detailEl = document.createElement('div');
        detailEl.className = 'antigravity-log-detail';
        detailEl.style.display = 'none';
        
        const responseText = tc.response || 'Running...';
        detailEl.innerHTML = `
            <pre><code>${responseText}</code></pre>
        `;
        
        itemEl.onclick = (e) => {
            e.stopPropagation();
            const isExpanded = detailEl.style.display === 'block';
            detailEl.style.display = isExpanded ? 'none' : 'block';
        };
        
        body.appendChild(itemEl);
        body.appendChild(detailEl);
    });
}

// --- stopToolPolling ---
function stopToolPolling() {
    if (toolPollInterval) {
        clearInterval(toolPollInterval);
        toolPollInterval = null;
    }
    // Hide modal if open when request terminates
    document.getElementById('tool-confirm-modal').style.display = 'none';
}

// --- showToolConfirmModal ---
function showToolConfirmModal(callId, toolName, details) {
    currentPendingCallId = callId;
    document.getElementById('tool-confirm-name').textContent = toolName;
    document.getElementById('tool-confirm-details').textContent = details;
    
    const modal = document.getElementById('tool-confirm-modal');
    modal.style.display = 'flex';
}

// --- respondToToolCall ---
async function respondToToolCall(status) {
    if (!currentPendingCallId) return;
    const callId = currentPendingCallId;
    currentPendingCallId = null;
    
    // Hide modal immediately
    document.getElementById('tool-confirm-modal').style.display = 'none';

    if (status === 'approved') {
        hasApprovedToolThisTurn = true;
    }
    
    try {
        await fetch('/approve_tool', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_id: callId,
                status: status
            })
        });
    } catch (e) {
        console.error("Error sending tool approval:", e);
    }
    
    // Resume polling for subsequent tool calls
    startToolPolling();
}

/* ==========================================================================
   XII. 11. DATABANK RAG SYSTEM
   ========================================================================== */

// --- openDataBank ---
async function openDataBank() {
    document.getElementById('databank-modal').style.display = 'flex';
    switchDataBankTab('upload');
    loadDataBankFiles();
    loadProjectSettings();
    if (!currentEditingProgramId) {
        try {
            const res = await fetch(`/history?session_id=default&t=${Date.now()}`);
            const data = await res.json();
            if (data.active_program) {
                currentEditingProgramId = data.active_program;
            }
        } catch (e) {
            console.error('openDataBank: failed to resolve active program', e);
        }
    }
    loadProgramJournals();
}

// --- closeDataBank ---
function closeDataBank() {
    document.getElementById('databank-modal').style.display = 'none';
}

// --- openQuestLog ---
async function openQuestLog() {
    document.getElementById('quest-modal').style.display = 'flex';
    switchQuestModalTab('journal');
    await loadQuests();
}

let questModalMouseDownTarget = null;
document.addEventListener('mousedown', (e) => {
    questModalMouseDownTarget = e.target;
}, true);

// --- closeQuestLog ---
function closeQuestLog(e) {
    if (hadMapDrag || isMapPanning) {
        hadMapDrag = false;
        return;
    }
    const modal = document.getElementById('quest-modal');
    if (e && modal) {
        if (e.target !== modal || questModalMouseDownTarget !== modal) {
            return;
        }
    }
    if (modal) modal.style.display = 'none';
}

// --- Map Pan & Zoom Variables ---
let mapZoom = 1.0;
let mapPanX = 0;
let mapPanY = 0;
let isMapPanning = false;
let hadMapDrag = false;
let mapStartX = 0;
let mapStartY = 0;

function clampTamrielMapPan() {
    const viewport = document.getElementById('tamriel-map-viewport');
    if (!viewport) return;
    const w = viewport.clientWidth;
    const h = viewport.clientHeight;

    if (mapZoom <= 1.0) {
        mapZoom = 1.0;
        mapPanX = 0;
        mapPanY = 0;
        return;
    }

    const minPanX = -w * (mapZoom - 1.0);
    const maxPanX = 0;
    const minPanY = -h * (mapZoom - 1.0);
    const maxPanY = 0;

    mapPanX = Math.min(Math.max(mapPanX, minPanX), maxPanX);
    mapPanY = Math.min(Math.max(mapPanY, minPanY), maxPanY);
}

function updateTamrielMapTransform() {
    clampTamrielMapPan();
    const layer = document.getElementById('tamriel-map-layer');
    const zoomDisplay = document.getElementById('tamriel-map-zoom-level');
    const viewport = document.getElementById('tamriel-map-viewport');
    if (layer) {
        layer.style.transform = `translate(${mapPanX}px, ${mapPanY}px) scale(${mapZoom})`;
    }
    if (zoomDisplay) {
        zoomDisplay.textContent = `${Math.round(mapZoom * 100)}%`;
    }
    if (viewport && !isMapPanning) {
        viewport.style.cursor = mapZoom > 1.0 ? 'grab' : 'default';
    }
}

function tamrielMapZoomIn() {
    const viewport = document.getElementById('tamriel-map-viewport');
    const w = viewport ? viewport.clientWidth : 0;
    const h = viewport ? viewport.clientHeight : 0;
    const newZoom = Math.min(mapZoom * 1.3, 5.0);
    if (w && h && mapZoom > 0) {
        const centerX = w / 2;
        const centerY = h / 2;
        mapPanX = centerX - (centerX - mapPanX) * (newZoom / mapZoom);
        mapPanY = centerY - (centerY - mapPanY) * (newZoom / mapZoom);
    }
    mapZoom = newZoom;
    updateTamrielMapTransform();
}

function tamrielMapZoomOut() {
    const viewport = document.getElementById('tamriel-map-viewport');
    const w = viewport ? viewport.clientWidth : 0;
    const h = viewport ? viewport.clientHeight : 0;
    const newZoom = Math.max(mapZoom / 1.3, 1.0);
    if (w && h && mapZoom > 0) {
        const centerX = w / 2;
        const centerY = h / 2;
        mapPanX = centerX - (centerX - mapPanX) * (newZoom / mapZoom);
        mapPanY = centerY - (centerY - mapPanY) * (newZoom / mapZoom);
    }
    mapZoom = newZoom;
    updateTamrielMapTransform();
}

function tamrielMapReset() {
    mapZoom = 1.0;
    mapPanX = 0;
    mapPanY = 0;
    updateTamrielMapTransform();
}

function initTamrielMapPanZoom() {
    const viewport = document.getElementById('tamriel-map-viewport');
    if (!viewport || viewport.dataset.panZoomInit) return;
    viewport.dataset.panZoomInit = "true";

    // Mouse Wheel Zoom centered on cursor
    viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
        const newZoom = Math.min(Math.max(mapZoom * zoomFactor, 1.0), 5.0);

        if (mapZoom > 0) {
            mapPanX = mouseX - (mouseX - mapPanX) * (newZoom / mapZoom);
            mapPanY = mouseY - (mouseY - mapPanY) * (newZoom / mapZoom);
        }
        mapZoom = newZoom;

        updateTamrielMapTransform();
    }, { passive: false });

    // Mouse Down (Drag Start)
    viewport.addEventListener('mousedown', (e) => {
        if (e.button !== 0 || mapZoom <= 1.0) return;
        isMapPanning = true;
        mapStartX = e.clientX - mapPanX;
        mapStartY = e.clientY - mapPanY;
        viewport.style.cursor = 'grabbing';
    });

    // Mouse Move (Pan)
    window.addEventListener('mousemove', (e) => {
        if (!isMapPanning) return;
        mapPanX = e.clientX - mapStartX;
        mapPanY = e.clientY - mapStartY;
        updateTamrielMapTransform();
    });

    // Mouse Up (Drag End)
    window.addEventListener('mouseup', () => {
        if (isMapPanning) {
            isMapPanning = false;
            hadMapDrag = true;
            setTimeout(() => { hadMapDrag = false; }, 200);
            const vp = document.getElementById('tamriel-map-viewport');
            if (vp) vp.style.cursor = mapZoom > 1.0 ? 'grab' : 'default';
        }
    });

    // Touch Support for Mobile
    let touchStartDist = 0;
    viewport.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1 && mapZoom > 1.0) {
            isMapPanning = true;
            mapStartX = e.touches[0].clientX - mapPanX;
            mapStartY = e.touches[0].clientY - mapPanY;
        } else if (e.touches.length === 2) {
            isMapPanning = false;
            touchStartDist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
        }
    }, { passive: true });

    viewport.addEventListener('touchmove', (e) => {
        if (isMapPanning && e.touches.length === 1) {
            mapPanX = e.touches[0].clientX - mapStartX;
            mapPanY = e.touches[0].clientY - mapStartY;
            updateTamrielMapTransform();
        } else if (e.touches.length === 2 && touchStartDist > 0) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            const factor = dist / touchStartDist;
            const newZoom = Math.min(Math.max(mapZoom * (factor > 1 ? 1.04 : 0.96), 1.0), 5.0);
            mapZoom = newZoom;
            updateTamrielMapTransform();
        }
    }, { passive: true });

    viewport.addEventListener('touchend', () => {
        isMapPanning = false;
        touchStartDist = 0;
    });
}

// --- switchQuestModalTab ---
function switchQuestModalTab(tabName) {
    const journalTabBtn = document.getElementById('quest-tab-btn-journal');
    const mapTabBtn = document.getElementById('quest-tab-btn-map');
    const journalContent = document.getElementById('quest-tab-content-journal');
    const mapContent = document.getElementById('quest-tab-content-map');
    const modalCard = document.querySelector('#quest-modal .modal-card');

    if (!journalTabBtn || !mapTabBtn || !journalContent || !mapContent) return;

    if (tabName === 'map') {
        if (modalCard) modalCard.style.maxWidth = '820px';

        mapTabBtn.style.background = 'hsla(215, 5%, 100%, 0.08)';
        mapTabBtn.style.color = 'var(--primary-accent)';
        mapTabBtn.style.borderColor = 'var(--primary-accent)';

        journalTabBtn.style.background = 'hsla(215, 5%, 100%, 0.05)';
        journalTabBtn.style.color = 'var(--text-muted)';
        journalTabBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.1)';

        journalContent.style.display = 'none';
        mapContent.style.display = 'block';

        renderTamrielMap();
    } else {
        if (modalCard) modalCard.style.maxWidth = '580px';

        journalTabBtn.style.background = 'hsla(215, 5%, 100%, 0.08)';
        journalTabBtn.style.color = 'var(--primary-accent)';
        journalTabBtn.style.borderColor = 'var(--primary-accent)';

        mapTabBtn.style.background = 'hsla(215, 5%, 100%, 0.05)';
        mapTabBtn.style.color = 'var(--text-muted)';
        mapTabBtn.style.borderColor = 'hsla(215, 5%, 100%, 0.1)';

        journalContent.style.display = 'block';
        mapContent.style.display = 'none';
    }
}




// --- loadQuests ---
async function loadQuests() {
    const container = document.getElementById('quests-container');
    if (!container) return;
    
    try {
        const response = await fetch('/api/quests');
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<p style="color: var(--danger-bright); font-size: 0.85rem; text-align: center; margin: 20px 0;">Error loading quests: ${data.error}</p>`;
            return;
        }
        
        const quests = data.quests || [];
        
        if (!quests || quests.length === 0) {
            container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin: 20px 0;">No active quests. Ask your program to assign you one!</p>`;
            return;
        }
        
        container.innerHTML = quests.map(quest => {
            const objectivesHtml = (quest.objectives || []).map(obj => 
                `<li style="margin-bottom: 8px; color: var(--text-main); font-size: 0.84rem; line-height: 1.4; display: flex; align-items: flex-start; gap: 8px;">
                    <span style="display: inline-block; width: 12px; height: 12px; border: 1.5px solid hsla(42, 90%, 56%, 0.6); border-radius: 2px; margin-top: 3px; flex-shrink: 0; background: hsla(42, 90%, 56%, 0.08);"></span>
                    <span>${obj}</span>
                </li>`
            ).join('');
            
            return `
                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                        <h4 style="margin: 0; color: var(--primary-accent); font-size: 0.98rem; font-weight: 600; letter-spacing: 0.01em;">${quest.title}</h4>
                        <span style="font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: var(--primary-glow); color: var(--primary-accent); border: 1px solid var(--border-color);">ACTIVE</span>
                    </div>
                    <div style="display: flex; gap: 16px; font-size: 0.78rem; color: var(--text-muted); flex-wrap: wrap;">
                        ${quest.location ? `<div><strong style="color: var(--text-muted);">Location:</strong> <span style="color: var(--text-main);">${quest.location}</span></div>` : ''}
                        ${quest.due ? `<div><strong style="color: var(--text-muted);">Status:</strong> <span style="color: var(--text-main);">${quest.due}</span></div>` : ''}
                    </div>
                    <div style="margin-top: 4px; padding-top: 8px; border-top: 1px solid hsla(215, 5%, 100%, 0.06);">
                        <ul style="margin: 6px 0 0 0; padding: 0; list-style: none;">
                            ${objectivesHtml}
                        </ul>
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) {
        console.error("Error loading quests:", e);
        container.innerHTML = `<p style="color: var(--danger-bright); font-size: 0.85rem; text-align: center; margin: 20px 0;">Failed to load quests.</p>`;
    }
}

// --- downloadQuest ---
function downloadQuest(questId) {
    window.open(`/api/quests/${questId}/download`, '_blank');
}

// --- deleteQuest ---
async function deleteQuest(questId) {
    showCustomConfirm(
        "Delete Quest",
        "Are you sure you want to permanently delete this quest? Your program will not be notified.",
        async () => {
            try {
                const response = await fetch(`/api/quests/${questId}/delete`, { method: 'POST' });
                const data = await response.json();
                if (data.status === 'success') {
                    await loadQuests();
                } else {
                    showCustomAlert("Error", "Failed to delete quest: " + (data.error || 'unknown error'));
                }
            } catch (e) {
                console.error("Error deleting quest:", e);
                showCustomAlert("Error", "Error deleting quest.");
            }
        }
    );
}

// --- completeQuest ---
async function completeQuest(questId) {
    
    try {
        const response = await fetch(`/api/quests/${questId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        
        const title = data.title || "Quest";
        const objectives = data.objectives || [];
        const objText = objectives.length > 0 ? ` with objectives: ${objectives.join(', ')}` : "";
        const systemMessage = `[SYSTEM: User has completed the quest: "${title}"${objText}]`;
        const questMsgId = 'quest_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
        
        // Append message locally (invisible/hidden user message)
        appendMessage('user', systemMessage, null, null, false, Date.now() / 1000, null, false, questMsgId);
        
        // Reload quest list UI
        await loadQuests();
        
    } catch (error) {
        console.error("Error completing quest:", error);
        showCustomAlert("Error", "Error completing quest: " + error.message);
    }
}

// --- switchDataBankTab ---
function switchDataBankTab(tab) {
    const uploadTab = document.getElementById('databank-tab-upload');
    const memoriesTab = document.getElementById('databank-tab-memories');
    const lorebooksTab = document.getElementById('databank-tab-lorebooks');
    const docsContainer = document.getElementById('databank-documents-container');
    const uploadBtn = document.getElementById('tab-btn-upload');
    const memoriesBtn = document.getElementById('tab-btn-memories');
    const lorebooksBtn = document.getElementById('tab-btn-lorebooks');
    const descriptor = document.getElementById('databank-descriptor');

    const descriptors = {
        upload: "Companion backstory, documents, and personal lore (Follower-linked).",
        memories: "Keyword-triggered journals and compacted memories linked to this game save.",
        lorebooks: "Global world info, game setting lore, and mechanics encyclopedia shared across saves."
    };

    if (descriptor && descriptors[tab]) {
        descriptor.textContent = descriptors[tab];
    }

    // Reset all buttons
    [uploadBtn, memoriesBtn, lorebooksBtn].forEach(btn => {
        if (btn) {
            btn.style.background = 'hsla(215, 5%, 100%, 0.05)';
            btn.style.color = 'var(--text-muted)';
            btn.style.border = '1px solid hsla(215, 5%, 100%, 0.1)';
        }
    });

    // Hide all tabs
    [uploadTab, memoriesTab, lorebooksTab].forEach(t => {
        if (t) t.style.display = 'none';
    });

    if (docsContainer) {
        docsContainer.style.display = (tab === 'upload') ? 'flex' : 'none';
    }

    const activate = (el, btn) => {
        if (el) el.style.display = 'flex';
        if (btn) {
            btn.style.background = 'hsla(215, 5%, 100%, 0.08)';
            btn.style.color = 'var(--primary-accent)';
            btn.style.border = '1px solid var(--primary-accent)';
        }
    };

    if (tab === 'upload') {
        activate(uploadTab, uploadBtn);
        loadDataBankFiles();
    } else if (tab === 'memories') {
        activate(memoriesTab, memoriesBtn);
        loadProgramJournals();
    } else if (tab === 'lorebooks') {
        activate(lorebooksTab, lorebooksBtn);
        loadLorebooks();
    }
}

// --- Lorebook management ---

async function loadLorebooks() {
    const container = document.getElementById('lorebooks-list-container');
    if (!container) return;
    container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem;">Loading...</p>';
    try {
        const res = await fetch('/api/lorebooks');
        const data = await res.json();
        const books = data.lorebooks || [];
        if (!books.length) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem;">No lorebooks loaded. Import a SillyTavern World Info JSON to get started.</p>';
            return;
        }
        container.innerHTML = '';
        for (const book of books) {
            container.appendChild(buildLorebookCard(book));
        }
    } catch (e) {
        container.innerHTML = `<p style="color: var(--danger-color); font-size: 0.8rem;">Error loading lorebooks.</p>`;
    }
}

function buildLorebookCard(book) {
    const card = document.createElement('div');
    card.style.cssText = 'background: var(--glass-bg-light); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden;';

    // Header row
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; cursor: pointer; user-select: none;';
    const nameSpan = document.createElement('div');
    nameSpan.style.cssText = 'display: flex; flex-direction: column; gap: 2px;';
    const scopeLabel = book.scope || (book.source === 'world' ? 'World & Rules' : (book.source === 'card' ? 'Follower Card' : 'Follower Custom'));
    const scopeColor = book.source === 'world' ? 'var(--arena-gold)' : 'var(--primary-accent)';
    nameSpan.innerHTML = `
        <span style="font-size: 0.85rem; color: var(--text-main); font-weight: 500;">${book.name}</span>
        <span style="font-size: 0.75rem; color: var(--text-muted);">${book.entry_count} entr${book.entry_count === 1 ? 'y' : 'ies'} &bull; <span style="color: ${scopeColor}; font-weight: 500;">${scopeLabel}</span></span>
    `;
    const headerActions = document.createElement('div');
    headerActions.style.cssText = 'display: flex; gap: 6px; align-items: center;';

    const chevron = document.createElement('span');
    chevron.textContent = '▸';
    chevron.style.cssText = 'color: var(--text-muted); font-size: 0.75rem; transition: transform 0.2s;';

    if (book.source === 'card') {
        const exportBtn = document.createElement('button');
        exportBtn.className = 'action-icon-btn';
        exportBtn.title = 'Export embedded lorebook';
        exportBtn.style.cssText = 'width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;';
        exportBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display:block"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"></path></svg>`;
        exportBtn.onclick = e => { e.stopPropagation(); window.location.href = `/api/programs/${encodeURIComponent(book.program_id || '')}/export/lorebook`; };
        headerActions.appendChild(exportBtn);
    }
    if (book.source === 'file') {
        const exportBtn = document.createElement('button');
        exportBtn.className = 'action-icon-btn';
        exportBtn.title = 'Export lorebook';
        exportBtn.style.cssText = 'width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;';
        exportBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display:block"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"></path></svg>`;
        exportBtn.onclick = e => { e.stopPropagation(); window.location.href = `/api/lorebooks/${encodeURIComponent(book.filename)}/export`; };
        const delBtn = document.createElement('button');
        delBtn.className = 'action-icon-btn';
        delBtn.title = 'Delete lorebook';
        delBtn.style.cssText = 'width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;';
        delBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
        delBtn.onclick = e => { e.stopPropagation(); deleteLorebook(book.filename, book.name); };
        headerActions.appendChild(exportBtn);
        headerActions.appendChild(delBtn);
    }
    headerActions.appendChild(chevron);
    header.appendChild(nameSpan);
    header.appendChild(headerActions);

    // Entry editor panel (hidden by default)
    const panel = document.createElement('div');
    panel.style.cssText = 'display: none; flex-direction: column; gap: 0; border-top: 1px solid var(--border-color);';

    let expanded = false;
    let entriesCache = null;

    header.onclick = async () => {
        expanded = !expanded;
        chevron.style.transform = expanded ? 'rotate(90deg)' : '';
        if (expanded) {
            panel.style.display = 'flex';
            if (!entriesCache) {
                panel.innerHTML = '<p style="padding: 12px 14px; color: var(--text-muted); font-size: 0.8rem;">Loading entries...</p>';
                const url = book.source === 'card'
                    ? '/api/lorebooks/card/entries'
                    : `/api/lorebooks/${encodeURIComponent(book.filename)}/entries`;
                const saveUrl = book.source === 'card'
                    ? '/api/lorebooks/card/save'
                    : `/api/lorebooks/${encodeURIComponent(book.filename)}/save`;
                try {
                    const r = await fetch(url);
                    const d = await r.json();
                    entriesCache = d.entries || [];
                } catch { entriesCache = []; }
                renderEntries(panel, entriesCache, saveUrl);
            }
        } else {
            panel.style.display = 'none';
        }
    };

    card.appendChild(header);
    card.appendChild(panel);
    return card;
}

function renderEntries(panel, entries, saveUrl) {
    panel.innerHTML = '';

    // Scrollable entries list
    const list = document.createElement('div');
    list.style.cssText = 'display: flex; flex-direction: column;';

    // Working copy for edits
    const working = entries.map(e => ({
        keys: (e.keys || e.key || []).join(', '),
        secondary_keys: (e.secondary_keys || e.keysecondary || []).join(', '),
        content: e.content || '',
        constant: !!e.constant,
        enabled: e.enabled !== false,
        name: e.name || e.comment || '',
        insertion_order: e.insertion_order ?? e.order ?? 100,
        position: e.position ?? 'before_char',
        _raw: e
    }));

    const rebuild = () => renderEntries(panel, working.map(w => ({
        keys: w.keys.split(',').map(k => k.trim()).filter(Boolean),
        content: w.content, constant: w.constant, enabled: w.enabled,
        name: w.name, insertion_order: w.insertion_order, position: w.position
    })), saveUrl);

    if (!working.length) {
        list.innerHTML = '<p style="padding: 12px 14px; color: var(--text-muted); font-size: 0.8rem;">No entries.</p>';
    }

    working.forEach((entry, idx) => {
        const row = document.createElement('div');
        row.style.cssText = 'padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); display: flex; flex-direction: column; gap: 6px;';

        const labelRow = document.createElement('div');
        labelRow.style.cssText = 'display: flex; align-items: center; justify-content: space-between; gap: 8px;';

        const nameInput = document.createElement('input');
        nameInput.value = entry.name;
        nameInput.placeholder = 'Entry name';
        nameInput.style.cssText = 'flex: 1; background: transparent; border: none; border-bottom: 1px solid var(--border-light); color: var(--text-main); font-size: 0.8rem; font-weight: 500; padding: 2px 0; outline: none;';
        nameInput.oninput = () => { working[idx].name = nameInput.value; };

        const constLabel = document.createElement('label');
        constLabel.style.cssText = 'display: flex; align-items: center; gap: 4px; font-size: 0.75rem; color: var(--text-muted); cursor: pointer; white-space: nowrap;';
        const constCheck = document.createElement('input');
        constCheck.type = 'checkbox';
        constCheck.checked = entry.constant;
        constCheck.style.accentColor = 'var(--primary-accent)';
        constCheck.onchange = () => { working[idx].constant = constCheck.checked; };
        constLabel.appendChild(constCheck);
        constLabel.appendChild(document.createTextNode(' Always on'));

        labelRow.appendChild(nameInput);
        labelRow.appendChild(constLabel);

        const deleteEntryBtn = document.createElement('button');
        deleteEntryBtn.className = 'action-icon-btn';
        deleteEntryBtn.title = 'Delete entry';
        deleteEntryBtn.style.cssText = 'width: 24px; height: 24px; border-radius: 5px; flex-shrink: 0;';
        deleteEntryBtn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
        deleteEntryBtn.onclick = () => { working.splice(idx, 1); rebuild(); };
        labelRow.appendChild(deleteEntryBtn);

        const keysInput = document.createElement('input');
        keysInput.value = entry.keys;
        keysInput.placeholder = 'Keywords (comma-separated)';
        keysInput.style.cssText = 'width: 100%; background: var(--glass-bg-medium); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-main); font-size: 0.78rem; padding: 5px 8px; outline: none; box-sizing: border-box;';
        keysInput.oninput = () => { working[idx].keys = keysInput.value; };

        const contentInput = document.createElement('textarea');
        contentInput.value = entry.content;
        contentInput.placeholder = 'Content injected into context when triggered';
        contentInput.style.cssText = 'width: 100%; background: var(--glass-bg-medium); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-main); font-size: 0.78rem; padding: 6px 8px; resize: vertical; min-height: 52px; outline: none; box-sizing: border-box; font-family: inherit;';
        contentInput.oninput = () => { working[idx].content = contentInput.value; };

        row.appendChild(labelRow);
        row.appendChild(keysInput);
        row.appendChild(contentInput);
        list.appendChild(row);
    });

    // Sticky footer — always visible below the scroll area
    const footer = document.createElement('div');
    footer.style.cssText = 'padding: 8px 14px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); flex-shrink: 0;';

    const addBtn = document.createElement('button');
    addBtn.className = 'dashed-action-btn';
    addBtn.style.cssText = 'width: auto; padding: 4px 14px; font-size: 0.78rem;';
    addBtn.textContent = '+ Add Entry';
    addBtn.onclick = () => {
        working.push({ keys: '', secondary_keys: '', content: '', constant: false, enabled: true, name: 'New Entry', insertion_order: 100, position: 'before_char', _raw: {} });
        rebuild();
        // Scroll new entry into view
        setTimeout(() => { list.scrollTop = list.scrollHeight; }, 50);
    };

    const saveBtn = document.createElement('button');
    saveBtn.className = 'onboarding-btn';
    saveBtn.style.cssText = 'padding: 5px 14px; font-size: 0.78rem; min-width: auto; width: auto; height: auto; margin: 0;';
    saveBtn.textContent = 'Save';
    saveBtn.onclick = async () => {
        const payload = working.map(w => ({
            ...(w._raw || {}),
            name: w.name,
            keys: w.keys.split(',').map(k => k.trim()).filter(Boolean),
            secondary_keys: w.secondary_keys.split(',').map(k => k.trim()).filter(Boolean),
            content: w.content,
            constant: w.constant,
            enabled: w.enabled,
            insertion_order: w.insertion_order,
            position: w.position,
        }));
        try {
            const r = await fetch(saveUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entries: payload })
            });
            const d = await r.json();
            if (d.success) {
                saveBtn.textContent = 'Saved ✓';
                setTimeout(() => { saveBtn.textContent = 'Save'; }, 1800);
            } else {
                showCustomAlert('Save failed', d.error || 'Unknown error');
            }
        } catch (e) { showCustomAlert('Save failed', e.message); }
    };

    footer.appendChild(addBtn);
    footer.appendChild(saveBtn);
    panel.appendChild(list);
    panel.appendChild(footer);
}


async function importLorebook(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res = await fetch('/api/lorebooks/import', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
            showCustomAlert('Lorebook imported', `"${file.name}" has been imported successfully.`);
            loadLorebooks();
        } else {
            showCustomAlert('Import failed', data.error || 'Unknown error');
        }
    } catch (e) {
        showCustomAlert('Import failed', e.message);
    }
    event.target.value = '';
}

async function deleteLorebook(filename, name) {
    if (!confirm(`Delete lorebook "${name}"?`)) return;
    try {
        const res = await fetch(`/api/lorebooks/${encodeURIComponent(filename)}/delete`, { method: 'POST' });
        const data = await res.json();
        if (data.success) loadLorebooks();
        else showCustomAlert('Delete failed', data.error || 'Unknown error');
    } catch (e) {
        showCustomAlert('Delete failed', e.message);
    }
}


// --- Project Settings JS Methods ---
let currentProjectSettings = {
    folders: [],
    security_preset: "ask_always",
    artifact_review_policy: "ask_always",
    search_engine: "web_crawling",
    searxng_url: "",
    tts_voice: "af_heart"
};

function toggleSearxUrlVisibility() {
    const engine = document.getElementById('project-search-engine').value;
    const container = document.getElementById('searxng-url-container');
    if (container) {
        if (engine === 'web_crawling') {
            container.style.display = 'flex';
        } else {
            container.style.display = 'none';
        }
    }
}

async function loadProjectSettings() {
    try {
        const res = await fetch('/api/project_settings');
        const data = await res.json();
        if (data.error) {
            console.error("Error loading project settings:", data.error);
            return;
        }
        currentProjectSettings = data;
        
        // Populate form controls
        let secPreset = data.security_preset || 'ask_always';
        if (secPreset === 'turbo') secPreset = 'auto';
        document.getElementById('project-security-preset').value = secPreset;
        document.getElementById('project-review-policy').value = data.artifact_review_policy || 'ask_always';
        document.getElementById('project-search-engine').value = data.search_engine || 'web_crawling';
        document.getElementById('project-searxng-url').value = data.searxng_url || '';
        
        toggleSearxUrlVisibility();
        renderProjectFolders();
    } catch (e) {
        console.error("Failed to load project settings:", e);
    }
}

function renderProjectFolders() {
    const list = document.getElementById('project-folders-list');
    if (!list) return;
    list.innerHTML = '';
    
    currentProjectSettings.folders.forEach((folder, idx) => {
        const isDefault = idx === 0; // The first folder is the default workspace root
        const row = document.createElement('div');
        row.className = 'list-entry-row row-layout';
        row.style.fontFamily = 'monospace';
        
        row.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; color: var(--text-main); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">
                <span style="display: inline-flex; align-items: center; width: 14px; height: 14px; color: var(--text-muted); opacity: 0.85; vertical-align: middle;">${getLogIconSvg('folder')}</span>
                <span title="${folder}">${folder}</span>
            </div>
            ${isDefault ? '<span class="badge-default">Default</span>' : `
                <span onclick="removeProjectFolder('${folder.replace(/\\/g, '\\\\')}')" style="cursor: pointer; opacity: 0.6; font-size: 1.1rem; font-family: sans-serif; line-height: 1;" title="Remove Folder">&times;</span>
            `}
        `;
        list.appendChild(row);
    });
}

async function saveProjectSettings() {
    currentProjectSettings.security_preset = document.getElementById('project-security-preset').value;
    currentProjectSettings.artifact_review_policy = document.getElementById('project-review-policy').value;
    currentProjectSettings.search_engine = document.getElementById('project-search-engine').value;
    currentProjectSettings.searxng_url = document.getElementById('project-searxng-url').value;
    
    try {
        const res = await fetch('/api/project_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentProjectSettings)
        });
        const data = await res.json();
        if (data.error) {
            showCustomAlert("Error Saving Settings", data.error);
        } else {
            currentProjectSettings = data.settings;
            renderProjectFolders();
        }
    } catch (e) {
        console.error("Failed to save project settings:", e);
        showCustomAlert("Error Saving Settings", "Failed to connect to backend.");
    }
}

async function addProjectFolder() {
    const folderPath = prompt("Enter absolute path to additional workspace folder:");
    if (!folderPath || !folderPath.trim()) return;
    
    const cleanPath = folderPath.trim();
    if (currentProjectSettings.folders.includes(cleanPath)) {
        showCustomAlert("Folder Exists", "This folder is already in the workspace.");
        return;
    }
    
    currentProjectSettings.folders.push(cleanPath);
    await saveProjectSettings();
}

async function removeProjectFolder(folder) {
    currentProjectSettings.folders = currentProjectSettings.folders.filter(f => f !== folder);
    await saveProjectSettings();
}

// --- loadDataBankFiles ---
async function loadDataBankFiles() {
    const container = document.getElementById('databank-files-container');
    container.innerHTML = '<div style="padding: 15px; color: var(--text-muted); font-size: 0.8rem; text-align: center;">Loading files...</div>';
    try {
        const res = await fetch('/api/databank/files');
        const data = await res.json();
        if (data.error) {
            container.innerHTML = `<div style="padding: 15px; color: var(--danger-bright); font-size: 0.8rem; text-align: center;">Error: ${data.error}</div>`;
            return;
        }
        const files = data.files || [];
        if (files.length === 0) {
            container.innerHTML = '<div class="empty-state">Knowledge Base is empty.</div>';
            return;
        }
        
        container.innerHTML = '';
        files.forEach(file => {
            const row = document.createElement('div');
            row.className = 'file-list-entry';
            
            const formatBytes = (bytes) => {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const sizes = ['B', 'KB', 'MB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
            };
            
            const docTypeIcon = `<span style="display: inline-flex; align-items: center; width: 14px; height: 14px; color: var(--text-muted); opacity: 0.85; vertical-align: middle; margin-right: 6px;">${file.source_type === 'url' ? getLogIconSvg('webpage') : getLogIconSvg('file')}</span>`;
            const fileDate = new Date(file.timestamp * 1000).toLocaleDateString();
            
            row.innerHTML = `
                <div style="flex: 1; min-width: 0; padding-right: 10px;">
                    <div style="font-weight: 500; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${file.name}">
                        ${docTypeIcon}${file.name}
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 3px; display: flex; gap: 10px;">
                        <span>Size: ${formatBytes(file.size)}</span>
                        <span>Chunks: ${file.chunk_count}</span>
                        <span>Added: ${fileDate}</span>
                    </div>
                </div>
                <button onclick="deleteDataBankFile('${file.id}', event)" class="action-icon-btn" title="Delete from memory" style="width: 26px; height: 26px; border-radius: 6px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            `;
            container.appendChild(row);
        });
    } catch (e) {
        console.error("Error loading files:", e);
        container.innerHTML = '<div style="padding: 15px; color: var(--danger-bright); font-size: 0.8rem; text-align: center;">Failed to connect to server.</div>';
    }
}

// --- uploadDataBankFile ---
async function uploadDataBankFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const loader = document.getElementById('databank-loader');
    const loaderText = document.getElementById('databank-loader-text');
    const input = document.getElementById('databank-file-input');
    
    loaderText.textContent = `Indexing file '${file.name}'... (First boot may download sentence-transformers model)`;
    loader.style.display = 'flex';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch('/api/databank/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.error) {
            showCustomAlert("Upload Failed", `Could not index document:<br><code style="color: var(--danger-bright); font-size: 0.75rem;">${data.error}</code>`);
        }
    } catch (e) {
        console.error("Error uploading file:", e);
        showCustomAlert("Upload Error", "Could not connect to the server to index the document.");
    } finally {
        input.value = ''; // Reset input selection
        loader.style.display = 'none';
        loadDataBankFiles();
    }
}

// --- scrapeDataBankUrl ---
async function scrapeDataBankUrl() {
    const input = document.getElementById('databank-url-input');
    const url = input.value.trim();
    if (!url) return;
    
    const loader = document.getElementById('databank-loader');
    const loaderText = document.getElementById('databank-loader-text');
    
    loaderText.textContent = `Scraping and indexing '${url}'...`;
    loader.style.display = 'flex';
    
    try {
        const res = await fetch('/api/databank/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        if (data.error) {
            showCustomAlert("Scraping Failed", `Could not scrape URL:<br><code style="color: var(--danger-bright); font-size: 0.75rem;">${data.error}</code>`);
        } else {
            input.value = ''; // Reset input
        }
    } catch (e) {
        console.error("Error scraping URL:", e);
        showCustomAlert("Scraping Error", "Could not connect to server to scrape URL.");
    } finally {
        loader.style.display = 'none';
        loadDataBankFiles();
    }
}

// --- deleteDataBankFile ---
async function deleteDataBankFile(docId, event) {
    event.stopPropagation();
    try {
        const res = await fetch('/api/databank/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: docId })
        });
        const data = await res.json();
        if (data.error) {
            showCustomAlert("Delete Error", data.error);
        }
    } catch (e) {
        console.error("Error deleting file:", e);
    } finally {
        loadDataBankFiles();
    }
}

// --- purgeDataBank ---
function purgeDataBank() {
    showCustomConfirm("Purge Knowledge Base", "Are you sure you want to delete all indexed files and empty the program's vectorized memory?", async () => {
        const loader = document.getElementById('databank-loader');
        const loaderText = document.getElementById('databank-loader-text');
        loaderText.textContent = "Purging knowledge index...";
        loader.style.display = 'flex';
        try {
            await fetch('/api/databank/purge', { method: 'POST' });
        } catch (e) {
            console.error("Error purging database:", e);
        } finally {
            loader.style.display = 'none';
            loadDataBankFiles();
        }
    });
}

/* ==========================================================================
   XIII. PAGE EVENT HANDLERS & REGISTRATION LIFECYCLES
   ========================================================================== */

// --- generateMessageId ---

// --- escapeHtml ---

/* ==========================================================================
   III. 2. ONBOARDING & GLOBAL CONFIG CONTROLLERS
   ========================================================================== */

// --- initializeModelSelect ---

// --- showOnboardingCard ---

// --- saveConfigData ---

// --- saveOnboardingConfig ---

// --- saveModalConfig ---

// --- verifyConnections ---

// --- checkOnboardingStatus ---

// --- checkModalStatus ---

/* ==========================================================================
   IV. 3. SERVER CONTROL MIDDLEWARE
   ========================================================================== */

// --- installLocalLLM ---

// --- pollInstallStatus ---

// --- startLocalLLM ---

// --- stopLocalLLM ---

// --- stopComfyUI ---

// --- searchHFModels ---

// --- downloadHFModel ---

// --- pollDownloadProgress ---

// --- fetchAndRenderLocalModels ---

// --- unloadLocalModel ---

// --- loadLocalModelDirect ---

// --- deleteLocalModel ---

// --- downloadComfyCheckpoint ---

// --- pollComfyCheckpointDownloads ---

// --- installComfyUI ---

// --- startComfyUI ---

// --- resolveWorkflowDependencies ---

/* ==========================================================================
   V. 4. DYNAMIC UI ACCESSORIES & PROMPTS
   ========================================================================== */

// --- updateHeartState ---

// --- triggerHeartBurst ---

// --- updateInputGlow ---

// --- getProfileUrl ---

// --- updateProfileImages ---

// --- applyTheme ---

// --- updateConnectionStatus ---

// --- updateConnectionModalStatus ---

// --- updateComfyModalStatus ---

// --- openConnectionModal ---

// --- closeConnectionModal ---

// --- openUserProfileModal ---

// --- closeUserProfileModal ---

// --- changeModel ---

// --- showCustomAlert ---

// --- showCustomConfirm ---

// --- closeCustomDialog ---

/* ==========================================================================
   VI. 5. USER PROFILE MANAGEMENT
   ========================================================================== */

// --- loadUserProfiles ---

// --- onUserProfileSelectChange ---

// --- saveActiveUserProfile ---

/* ==========================================================================
   VII. 6. PROGRAM / PROGRAM SELECTION
   ========================================================================== */

// --- openAssistantModal ---

// --- closeAssistantModal ---

// --- openImportProgramModal ---

// --- closeImportProgramModal ---

// --- switchImportTab ---

// --- triggerTavernCardFileSelect ---

// --- handleTavernCardFileChange ---

// --- submitTavernCardImport ---

// --- submitDescriptionImport ---

// --- renderProgramsList ---

// --- selectAssistant ---

// --- deleteAssistant ---

/* ==========================================================================
   VIII. 7. CHAT SESSION & HISTORY CONTROLS
   ========================================================================== */

// --- showWelcomeMessage ---

// --- loadHistory ---

// --- resetSession ---

/* ==========================================================================
   IX. 8. MESSAGE RENDERING & POST-PROCESSING
   ========================================================================== */

// --- toggleAutoSpeak ---

// --- resetSpeakButtons ---

// --- speakMessage ---

// --- toggleThinkingBlock ---

// --- appendMessage ---

// --- postProcessMessageHTML ---

/* ==========================================================================
   X. 9. CHAT TURN PROCESSING
   ========================================================================== */

// --- triggerFileInput ---

// --- handleFileSelect ---

// --- clearAttachment ---

// --- sendMessage ---

// --- truncateChatAfter ---

// --- startEditMessage ---

// --- cancelMessageEdit ---

// --- saveMessageEdit ---

// --- resendUserMessage ---

// --- rerollFromMessage ---

// --- deleteTurnFromMessage ---

// --- reusePromptFromMessage ---

/* ==========================================================================
   XI. 10. TOOL INVOCATION & PORTRAITS
   ========================================================================== */

// --- fetchComfyCheckpoints ---

// --- changeComfyCheckpoint ---

// --- searchComfyHFCheckpoints ---

// --- loadServerImages ---

// --- getGalleryImages ---

// --- expandImage ---

// --- updateModalImage ---

// --- closeModal ---

// --- prevGalleryImage ---

// --- nextGalleryImage ---

// --- deleteCurrentImage ---

// --- handleTouchStart ---

// --- handleTouchEnd ---

// --- handleSwipeGesture ---

// --- generatePortraitPrompt ---

// --- regenerateImage ---

// --- startToolPolling ---

// --- stopToolPolling ---

// --- showToolConfirmModal ---

// --- respondToToolCall ---

/* ==========================================================================
   XII. 11. DATABANK RAG SYSTEM
   ========================================================================== */

// --- openDataBank ---

// --- closeDataBank ---

// --- switchDataBankTab ---

// --- loadDataBankFiles ---

// --- uploadDataBankFile ---

// --- scrapeDataBankUrl ---

// --- deleteDataBankFile ---

// --- purgeDataBank ---

/* ==========================================================================
   XIII. UNCATEGORIZED FUNCTIONS
   ========================================================================== */

// --- createNewUserProfilePrompt ---

/* ==========================================================================
   XIV. PAGE EVENT HANDLERS & REGISTRATION LIFECYCLES
   ========================================================================== */

let isGenerating = false;
let chatAbortController = null;

function setGenerating(val) {
    isGenerating = val;
    const sendBtn = document.querySelector('.send-btn');
    const stopBtn = document.querySelector('.stop-btn');
    if (val) {
        if (sendBtn) sendBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'flex';
    } else {
        if (sendBtn) sendBtn.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

async function cancelGeneration() {
    if (chatAbortController) {
        chatAbortController.abort();
        chatAbortController = null;
    }
    try {
        await fetch('/api/cancel_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch (e) {
        console.error("Error cancelling chat:", e);
    }
}

// Better textarea handling for mobile and desktop
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    updateInputGlow();
    sessionStorage.setItem('staged_message', this.value);
});

userInput.addEventListener('focus', updateInputGlow);
userInput.addEventListener('blur', updateInputGlow);

userInput.addEventListener('keydown', function(event) {
    // User requested Enter to always send only on desktop, while mobile requires pressing the send button
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.matchMedia('(max-width: 768px)').matches;
    if (event.key === 'Enter' && !event.shiftKey && !isMobile) {
        event.preventDefault();
        sendMessage();
    }
});

const imageInput = document.getElementById('image-input');
const previewArea = document.getElementById('preview-area');
const previewImg = document.getElementById('preview-img');
const previewFilename = document.getElementById('preview-filename');

let attachedBase64 = null;
let attachedMime = null;
let attachedMediaPath = null;
let hasApprovedToolThisTurn = false;

let profileCacheBuster = Date.now();

// Initialize session ID, reading from URL parameter if present for device syncing
const urlParams = new URLSearchParams(window.location.search);
const sessionFromUrl = !!urlParams.get('session_id');
let sessionId = urlParams.get('session_id');
if (sessionId) {
    safeLocalStorage.setItem('program_session_id', sessionId);
    // Clean up the URL query parameter so page reloads don't force it later
    try {
        window.history.replaceState({}, document.title, window.location.pathname);
    } catch (e) {}
} else {
    sessionId = safeLocalStorage.getItem('program_session_id') || 'default';
    safeLocalStorage.setItem('program_session_id', sessionId);
}

// Display session ID signature in header for easy verification
const sessionDisplay = document.getElementById('session-id-display');
if (sessionDisplay && sessionId) {
    sessionDisplay.textContent = `• ID: ${sessionId.slice(-4)}`;
    sessionDisplay.title = `Full Session ID: ${sessionId}`;
}

// Retrieve selected model from localStorage or use default
let selectedModel = safeLocalStorage.getItem('program_selected_model') || 'local-llm';
let lastInteractionTime = Date.now();
let hasTriggeredProactive = false;
let proactiveAbortController = null;
let activeProgramName = "";
let activeProgram = "ria_silmane";
let availableModels = [];
let connectionStatus = { remote_configured: false, gemini_configured: false, local_online: false };
let modelInitPromise = null;

let comfyStatus = { installed: false, running: false, resolution_status: { status: "idle", progress: "", errors: [] } };

// Concurrency guards for ComfyUI operations
let _comfyUpdateRunning = false;
let _comfyUpdateTimer = null;
let _comfyStarting = false;
let _comfyStopping = false;
let _localStarting = false;
let _localStopping = false;
let _comfyResolving = false;
let _comfyCheckpointsInitialized = false;

let comfyDownloadTimer = null;

let userProfiles = [];
let activeUserProfile = "";

// Initialize model selection on script load
modelInitPromise = initializeModelSelect();

// --- SSE Live Connection Status Stream ---
let sseStarted = false;
let evtSource = null;

function startSSE() {
    if (sseStarted) return;
    sseStarted = true;

    function connect() {
        if (evtSource) {
            evtSource.close();
        }
        evtSource = new EventSource('/api/events/status');
        evtSource.addEventListener('connection_status', (e) => {
            try {
                const payload = JSON.parse(e.data);
                const status = payload.status;
                updateConnectionStatus({
                    remote_configured: status.remote_configured,
                    remote_model: status.remote_model,
                    remote_url: status.remote_url,
                    local_online: status.local_online,
                    local_installed: status.local_installed,
                    temperature: status.temperature !== undefined ? status.temperature : connectionStatus.temperature,
                    env_path: status.env_path
                });
                // Update ComfyUI status from SSE payload directly
                comfyStatus.installed = status.comfy_installed;
                comfyStatus.running = status.comfy_running;
                // Refresh modal UI if the settings modal is open, using SSE data directly (skipFetch)
                const modal = document.getElementById('connection-modal');
                if (modal && modal.style.display !== 'none') {
                    updateConnectionModalStatus();
                    updateComfyModalStatus(true);
                }
                // Refresh model dropdown to reflect online/offline changes
                initializeModelSelect();
            } catch (err) {
                console.error('SSE parse error:', err);
            }
        });
        evtSource.onerror = () => {
            if (evtSource) {
                evtSource.close();
            }
            // Reconnect after 3 seconds
            setTimeout(connect, 3000);
        };
    }
    connect();

    async function refreshAllStatuses() {
        try {
            await initializeModelSelect();
            if (typeof updateComfyModalStatus === 'function') {
                await updateComfyModalStatus(false);
            }
        } catch (e) {
            console.error("Error refreshing statuses on focus:", e);
        }
    }

    // Reconnect or refresh on page visibility / focus to handle mobile sleep states
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            connect();
            refreshAllStatuses();
        }
    });

    window.addEventListener('focus', () => {
        if (document.visibilityState === 'visible') {
            refreshAllStatuses();
        }
    });
}

let serverImages = [];

let galleryImages = [];
let currentGalleryIndex = -1;

// Swipe gestures detection
let touchStartX = 0;
let touchEndX = 0;

// Bind keyboard navigation globally
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeModal();
        closeStatusModal();
        closeInventoryModal();
        return;
    }
    const modal = document.getElementById('image-modal');
    if (modal && modal.style.display === 'flex') {
        if (event.key === 'ArrowLeft') {
            prevGalleryImage();
        } else if (event.key === 'ArrowRight') {
            nextGalleryImage();
        }
    }
});

// Initialize swipe event listeners once the modal exists in DOM
function initModalListeners() {
    const modal = document.getElementById('image-modal');
    if (modal) {
        modal.addEventListener('touchstart', handleTouchStart, { passive: true });
        modal.addEventListener('touchend', handleTouchEnd, { passive: true });
    }
    // Init TTS toggle button state
    const ttsBtn = document.getElementById('tts-toggle-btn');
    if (ttsBtn && ttsAutoSpeak) {
        ttsBtn.classList.add('active');
    }
    initAudioSystem();
}
if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initModalListeners);
} else {
    initModalListeners();
}

// Proactive idle action trigger and functions
function resetIdleTimer() {
    lastInteractionTime = Date.now();
    hasTriggeredProactive = false;
    // Cancel any in-flight proactive request so stale responses never render
    if (proactiveAbortController) {
        proactiveAbortController.abort();
        proactiveAbortController = null;
    }
}

window.addEventListener('mousemove', resetIdleTimer);
window.addEventListener('click', resetIdleTimer);
window.addEventListener('keypress', resetIdleTimer);
window.addEventListener('touchstart', resetIdleTimer);

async function triggerProactiveAction() {
    // Create an abort controller for this request so user activity can cancel it
    proactiveAbortController = new AbortController();
    const signal = proactiveAbortController.signal;
    try {
        const response = await fetch('/api/proactive_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                model: selectedModel
            }),
            signal
        });
        // After the await, verify the request was not aborted during the LLM call
        if (signal.aborted) return;
        const data = await response.json();
        if (signal.aborted) return;
        if (data.status === 'success') {
            if (data.type === 'tip' || data.type === 'thought') {
                showThoughtBubbleOverlay(data.content);
            } else if (data.type === 'message' || data.type === 'portrait') {
                loadHistory();
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error("Proactive action error:", err);
    } finally {
        proactiveAbortController = null;
    }
}

function showThoughtBubbleOverlay(text) {
    hideThoughtBubbleOverlay(); // Remove existing if any
    
    const row = document.createElement('div');
    row.className = 'message-row program-row thought-row';
    row.id = 'active-thought-bubble';
    row.onclick = () => hideThoughtBubbleOverlay();
    
    const profileUrl = getProfileUrl();
    
    row.innerHTML = `
        <div class="avatar-container" style="opacity: 0.5;">
            <img class="avatar program-avatar thinking-glow" src="${profileUrl}" alt="Companion">
        </div>
        <div class="message program thought-bubble">
            <div class="thought-badge">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; display: inline-block; vertical-align: -1px;">
                    <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.26C17.81 13.47 19 11.38 19 9a7 7 0 0 0-7-7z"></path>
                </svg>
                <span>Tip</span>
            </div>
            <div class="message-text" style="font-style: italic; color: var(--text-muted); font-size: 0.9rem; line-height: 1.45;">
                ${text}
            </div>
        </div>
    `;
    
    chatContainer.appendChild(row);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideThoughtBubbleOverlay() {
    const bubble = document.getElementById('active-thought-bubble');
    if (bubble) {
        bubble.remove();
    }
    // Remove glow from all program avatars
    document.querySelectorAll('.program-avatar.thinking-glow').forEach(img => {
        img.classList.remove('thinking-glow');
    });
}

// Periodically check for inactivity (every 5 seconds)
setInterval(async () => {
    const idleTime = Date.now() - lastInteractionTime;
    // 3 minutes (180 seconds) of idle time triggers proactive check
    if (idleTime > 180000 && !hasTriggeredProactive) {
        hasTriggeredProactive = true;
        const userInput = document.getElementById('user-input');
        if (userInput && !userInput.disabled) {
            await triggerProactiveAction();
        }
    }
}, 5000);



// Load previous chat history on DOM ready
function initMainApp() {
    updateProfileImages();
    loadHistory();
    fetchCharacterStatus();
}
if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initMainApp);
} else {
    initMainApp();
}

// Global error listener to catch image load failures and switch to dynamic colored circles
window.addEventListener('error', function (e) {
    if (e.target && e.target.tagName === 'IMG' && (e.target.classList.contains('program-avatar') || e.target.classList.contains('program-list-avatar') || e.target.classList.contains('voice-call-avatar') || e.target.classList.contains('voice-call-program-avatar'))) {
        switchToCircleFallback(e.target);
    }
}, true);

function switchToCircleFallback(img) {
    let name = '';
    let color = '';
    let useAccent = false;
    
    if (img.classList.contains('program-list-avatar')) {
        name = img.getAttribute('data-name') || '';
        color = img.getAttribute('data-color') || '';
    } else {
        name = activeProgramName || '';
        if (!name) {
            const input = document.getElementById('user-input');
            if (input && input.placeholder && input.placeholder.startsWith('Ask ')) {
                name = input.placeholder.replace('Ask ', '');
            }
        }
        color = getComputedStyle(document.documentElement).getPropertyValue('--primary-accent').trim() || '#38bdf8';
        useAccent = true;
    }
    
    if (!name) name = 'Program';
    if (!color) color = '#4a3520';
    
    const fallback = document.createElement('div');
    // Copy classes
    fallback.className = img.className;
    fallback.classList.add('avatar-fallback');
    
    // Copy all original attributes to fallback div to preserve properties like src, data-*
    for (let attr of img.attributes) {
        if (attr.name !== 'class' && attr.name !== 'style') {
            fallback.setAttribute(attr.name, attr.value);
        }
    }
    
    // Determine size based on element class to prevent copying stretched layout dimensions
    let size = '48px';
    if (img.classList.contains('program-list-avatar')) {
        size = '44px';
    } else if (img.classList.contains('voice-call-avatar') || img.classList.contains('voice-call-program-avatar')) {
        size = '120px';
    }
    
    fallback.style.cssText = img.style.cssText;
    fallback.style.width = size;
    fallback.style.height = size;
    fallback.style.aspectRatio = '1 / 1';
    fallback.style.flexShrink = '0';
    fallback.style.borderRadius = '50%';
    
    if (useAccent) {
        fallback.style.backgroundColor = 'var(--primary-accent)';
        fallback.style.color = 'var(--primary-btn-text)';
    } else {
        fallback.style.backgroundColor = color;
        
        // Calculate text color brightness
        let hex = color.replace('#', '');
        if (hex.length === 3) {
            hex = hex.split('').map(c => c + c).join('');
        }
        let r = parseInt(hex.substring(0, 2), 16) || 0;
        let g = parseInt(hex.substring(2, 4), 16) || 0;
        let b = parseInt(hex.substring(4, 6), 16) || 0;
        let brightness = (r * 299 + g * 587 + b * 114) / 1000;
        fallback.style.color = brightness > 140 ? '#121214' : 'var(--text-bright)';
    }
    
    fallback.style.display = 'flex';
    fallback.style.alignItems = 'center';
    fallback.style.justifyContent = 'center';
    const isBright = useAccent ? (getComputedStyle(document.documentElement).getPropertyValue('--primary-btn-text').trim() === '#121214') : (fallback.style.color === '#121214');
    const silhouetteColor = isBright ? 'rgba(0,0,0,0.35)' : 'hsla(215, 5%, 100%, 0.3)';
    fallback.innerHTML = `
        <svg viewBox="0 0 24 24" style="width: 62%; height: 62%; fill: ${silhouetteColor}; display: block;">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
    `;
    fallback.onclick = img.onclick;
    
    if (img.parentNode) {
        img.parentNode.replaceChild(fallback, img);
    }
}

// Edit and Reroll functionality

// Custom modal helper functions for alert and confirm
let customDialogCallback = null;
let customDialogCancelCallback = null;

// Tool execution polling logic for web/mobile confirmation
let toolPollInterval = null;
let currentPendingCallId = null;

// --- VECTORIZED DATA BANK FUNCTIONS ---

// --- PROGRAM ASSISTANT SELECTION FUNCTIONS ---

let selectedTavernCardFile = null;



// Periodically verify all selects matching .glass-select are set up
setInterval(() => {
    document.querySelectorAll("select.glass-select").forEach(select => {
        if (!select.dataset.customDropdownSetup) {
            setupCustomDropdown(select);
        }
    });
}, 250);

// --- Voice Call Orchestrator ---
let isVoiceCallActive = false;
let voiceCallRecognition = null;
let voiceCallStartTime = 0;
let voiceCallTranscript = [];
let voiceCallMuted = false;
let voiceCallSpeakerMuted = false;
let voiceCallAnalyser = null;
let voiceCallUserAnalyser = null;
let voiceCallUserSource = null;
let consecutiveShortSessions = 0;
let lastRecognitionStartTime = 0;
let visualizerTime = 0;
let silenceTimer = null;
let currentSpeechText = "";
let lastUserSpeechTime = 0;

function playCallStartSound() {
    try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContextClass();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(260, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(520, ctx.currentTime + 0.3);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
    } catch(e) {
        console.error("Failed to play call start sound:", e);
    }
}

function playHangupSound() {
    try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContextClass();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(400, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.25);
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.25);
    } catch(e) {
        console.error("Failed to play hangup sound:", e);
    }
}

function startVoiceCall() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showCustomAlert("Secure Context Required", "Microphone access is only available over HTTPS or localhost. Please access the Arena using HTTPS or localhost to enable voice calls.");
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showCustomAlert("Speech Recognition Not Supported", "Your browser does not support Speech Recognition. Please try Chrome, Edge, or Safari.");
        return;
    }
    
    const overlay = document.getElementById('voice-call-overlay');
    overlay.style.display = 'flex';
    
    document.getElementById('voice-call-program-name').textContent = activeProgramName || "Program";
    const voiceAvatar = document.getElementById('voice-call-program-avatar');
    if (voiceAvatar) {
        updateAvatarElement(voiceAvatar, getProfileUrl());
    }
    
    updateVoiceCallStatus("Connecting...");
    document.getElementById('voice-call-transcript-turns').innerHTML = "";
    const transcriptWrapper = document.getElementById('voice-call-transcript');
    if (transcriptWrapper) {
        transcriptWrapper.style.display = 'none';
    }
    
    // Initialize separate voice call session on the backend
    fetch('/api/voice_call/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
    }).catch(e => console.error("Error starting voice session:", e));

    isVoiceCallActive = true;
    voiceCallStartTime = Date.now();
    voiceCallTranscript = [];
    voiceCallMuted = false;
    voiceCallSpeakerMuted = false;
    isProgramSpeaking = false;
    isProgramThinking = false;
    consecutiveShortSessions = 0;
    visualizerTime = 0;
    currentSpeechText = "";
    lastUserSpeechTime = 0;
    if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
    }
    
    // Capture user mic for dynamic audio-reactive visualization
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        voiceCallMicStream = stream;
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!voiceCallAudioContext) {
                voiceCallAudioContext = new AudioContextClass();
            }
            if (!voiceCallUserAnalyser) {
                voiceCallUserAnalyser = voiceCallAudioContext.createAnalyser();
                voiceCallUserAnalyser.fftSize = 64;
            }
            voiceCallUserSource = voiceCallAudioContext.createMediaStreamSource(stream);
            voiceCallUserSource.connect(voiceCallUserAnalyser);
        } catch(e) {
            console.warn("Could not setup user microphone visualizer node:", e);
        }
    }).catch(err => {
        console.warn("Could not capture user mic stream for visualization:", err);
    });
    
    document.getElementById('voice-call-mute-btn').classList.remove('disabled');
    document.getElementById('voice-call-speaker-btn').classList.remove('disabled');
    document.getElementById('voice-call-mute-btn').title = "Mute Microphone";
    document.getElementById('voice-call-speaker-btn').title = "Mute Speaker";
    
    // Mic access is managed directly by the SpeechRecognition engine below
    
    drawVisualizer();
    
    voiceCallRecognition = new SpeechRecognition();
    voiceCallRecognition.continuous = true;
    voiceCallRecognition.interimResults = true;
    voiceCallRecognition.lang = 'en-US';
    
    voiceCallRecognition.onstart = () => {
        updateVoiceCallStatus("Listening...");
        lastRecognitionStartTime = Date.now();
        currentSpeechText = "";
        playCallStartSound();
    };
    
    voiceCallRecognition.onresult = (event) => {
        if (!isVoiceCallActive || isProgramSpeaking || isProgramThinking || voiceCallMuted) return;
        
        let interimTranscript = "";
        let finalTranscript = "";
        
        for (let i = 0; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + " ";
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        const text = (finalTranscript + interimTranscript).trim();
        if (text) {
            currentSpeechText = text;
            updateVoiceCallStatus("Listening...");
            lastUserSpeechTime = Date.now(); // Track speech activity for visualizer ripple
            
            if (silenceTimer) clearTimeout(silenceTimer);
            silenceTimer = setTimeout(() => {
                if (currentSpeechText && isVoiceCallActive && !isProgramSpeaking && !isProgramThinking) {
                    const speechToProcess = currentSpeechText;
                    currentSpeechText = "";
                    processUserSpeech(speechToProcess);
                }
            }, 1300); // 1.3 seconds of silence -> send turn (prevents cut-off)
        }
    };
    
    let restartTimeout = null;
    voiceCallRecognition.onend = () => {
        const sessionDuration = Date.now() - lastRecognitionStartTime;
        console.log("Speech recognition session ended. Duration:", sessionDuration, "ms");
        
        // If session was shorter than 4 seconds, count as a failure
        if (sessionDuration < 4000) {
            consecutiveShortSessions++;
        } else {
            consecutiveShortSessions = 0;
        }
        
        if (consecutiveShortSessions >= 3) {
            console.error("Speech recognition session ended too quickly 3 times. Stopping call loop.");
            showCustomAlert("Speech Service Unavailable", "Your browser's speech recognition closed immediately. This usually happens if the speech service is not supported on this browser, blocked by settings, or lacks internet connection. Please try using Google Chrome on a secure connection (HTTPS/localhost).");
            endVoiceCall();
            return;
        }
        
        if (isVoiceCallActive && !isProgramSpeaking && !isProgramThinking && !voiceCallMuted) {
            updateVoiceCallStatus("Paused...");
            if (restartTimeout) clearTimeout(restartTimeout);
            restartTimeout = setTimeout(() => {
                if (isVoiceCallActive && !isProgramSpeaking && !isProgramThinking && !voiceCallMuted) {
                    try {
                        updateVoiceCallStatus("Listening...");
                        voiceCallRecognition.start();
                    } catch(e) {
                        console.error("Error restarting speech recognition:", e);
                    }
                }
            }, 1500); // 1.5-second cooldown
        }
    };
    
    voiceCallRecognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        
        // network is now treated as a fatal/critical error for transcription
        const fatalErrors = ['audio-capture', 'not-allowed', 'service-not-allowed', 'language-not-supported', 'bad-grammar', 'network'];
        if (fatalErrors.includes(event.error)) {
            let errMsg = "Speech recognition error: " + event.error;
            if (event.error === 'not-allowed') {
                errMsg = "Microphone access blocked. Please grant microphone permissions in your browser settings.";
            } else if (event.error === 'audio-capture') {
                errMsg = "No microphone detected. Please connect a microphone and try again.";
            } else if (event.error === 'service-not-allowed') {
                errMsg = "Speech recognition service is not allowed or supported by your browser.";
            } else if (event.error === 'language-not-supported') {
                errMsg = "Language not supported by the browser speech recognition service.";
            } else if (event.error === 'network') {
                errMsg = "Speech recognition network error. This browser requires an active internet connection to transcribe speech.";
            }
            showCustomAlert("Voice Call Error", errMsg);
            endVoiceCall();
        }
    };
    
    try {
        voiceCallRecognition.start();
    } catch(e) {
        console.error("Error starting recognition:", e);
    }
}

function updateVoiceCallStatus(text) {
    const statusEl = document.getElementById('voice-call-status');
    if (statusEl) {
        statusEl.textContent = text;
    }
}

function addVoiceCallTurn(speaker, text) {
    voiceCallTranscript.push({ speaker: speaker, text: text });
    
    const turnsContainer = document.getElementById('voice-call-transcript-turns');
    if (!turnsContainer) return;
    
    const turnDiv = document.createElement('div');
    turnDiv.className = 'voice-call-transcript-turn';
    
    const speakerSpan = document.createElement('span');
    speakerSpan.className = `turn-speaker ${speaker}`;
    speakerSpan.textContent = speaker === 'user' ? `${getUserDisplayName()}: ` : `${activeProgramName || 'Program'}: `;
    
    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    
    turnDiv.appendChild(speakerSpan);
    turnDiv.appendChild(textSpan);
    turnsContainer.appendChild(turnDiv);
    
    const transcriptWrapper = document.getElementById('voice-call-transcript');
    if (transcriptWrapper) {
        transcriptWrapper.style.display = 'block';
        transcriptWrapper.scrollTop = transcriptWrapper.scrollHeight;
    }
}

async function processUserSpeech(text) {
    if (!isVoiceCallActive) return;
    
    if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
    }
    currentSpeechText = "";
    
    addVoiceCallTurn('user', text);
    
    isProgramThinking = true;
    updateVoiceCallStatus(`${activeProgramName || 'Program'} is thinking...`);
    
    let shouldResume = false;
    try {
        if (voiceCallRecognition) {
            voiceCallRecognition.stop();
        }
        
        let voiceModel = selectedModel;
        if (connectionStatus && (connectionStatus.remote_configured ) && connectionStatus.remote_model) {
            voiceModel = connectionStatus.remote_model;
        }
        
        const payload = {
            message: text,
            session_id: sessionId + "_voice",
            model: voiceModel,
            is_voice_call: true
        };
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error("Chat request failed");
        const data = await response.json();
        
        if (!isVoiceCallActive) return;
        
        let replyText = data.response || "";
        if (replyText) {
            addVoiceCallTurn('program', replyText);
            updateVoiceCallStatus(`${activeProgramName || 'Program'} is speaking...`);
            await playProgramSpeech(replyText);
        } else {
            updateVoiceCallStatus("Listening...");
            shouldResume = true;
        }
    } catch(e) {
        console.error("Error in voice call turn processing:", e);
        updateVoiceCallStatus("Error. Listening...");
        shouldResume = true;
    } finally {
        isProgramThinking = false;
        if (shouldResume) {
            resumeVoiceRecognition();
        }
    }
}

async function playProgramSpeech(text) {
    if (voiceCallSpeakerMuted) {
        updateVoiceCallStatus("Listening...");
        resumeVoiceRecognition();
        return;
    }
    
    isProgramSpeaking = true;
    const tempMsgId = "voice-" + Date.now();
    
    try {
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: tempMsgId, text: text })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'TTS failed');
        }
        
        if (!isVoiceCallActive) return;
        
        if (voiceCallActiveAudio) {
            voiceCallActiveAudio.pause();
        }
        
        voiceCallActiveAudio = new Audio(data.audio_url);
        voiceCallActiveAudio.volume = isSpeechMuted ? 0 : speechVolume;
        
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!voiceCallAudioContext) {
                voiceCallAudioContext = new AudioContextClass();
            }
            if (!voiceCallAnalyser) {
                voiceCallAnalyser = voiceCallAudioContext.createAnalyser();
                voiceCallAnalyser.fftSize = 64;
            }
            const source = voiceCallAudioContext.createMediaElementSource(voiceCallActiveAudio);
            source.connect(voiceCallAnalyser);
            voiceCallAnalyser.connect(voiceCallAudioContext.destination);
        } catch(ae) {
            console.warn("Could not setup program audio visualizer node:", ae);
        }
        
        voiceCallActiveAudio.onended = () => {
            isProgramSpeaking = false;
            updateVoiceCallStatus("Listening...");
            resumeVoiceRecognition();
        };
        
        voiceCallActiveAudio.onerror = () => {
            console.error("Audio playback error");
            isProgramSpeaking = false;
            updateVoiceCallStatus("Listening...");
            resumeVoiceRecognition();
        };
        
        await voiceCallActiveAudio.play();
    } catch (err) {
        console.error("TTS generation or playback error:", err);
        isProgramSpeaking = false;
        updateVoiceCallStatus("Listening...");
        resumeVoiceRecognition();
    }
}

function resumeVoiceRecognition() {
    if (!isVoiceCallActive || isProgramSpeaking || isProgramThinking || voiceCallMuted) return;
    try {
        if (voiceCallRecognition) {
            voiceCallRecognition.start();
        }
    } catch(e) {}
}

function toggleCallMute() {
    voiceCallMuted = !voiceCallMuted;
    const btn = document.getElementById('voice-call-mute-btn');
    if (voiceCallMuted) {
        btn.classList.add('disabled');
        btn.title = "Unmute Microphone";
        updateVoiceCallStatus("Muted");
        if (voiceCallRecognition) {
            try { voiceCallRecognition.stop(); } catch(e) {}
        }
    } else {
        btn.classList.remove('disabled');
        btn.title = "Mute Microphone";
        updateVoiceCallStatus("Listening...");
        resumeVoiceRecognition();
    }
}

function toggleCallSpeaker() {
    voiceCallSpeakerMuted = !voiceCallSpeakerMuted;
    const btn = document.getElementById('voice-call-speaker-btn');
    if (voiceCallSpeakerMuted) {
        btn.classList.add('disabled');
        btn.title = "Unmute Speaker";
        if (voiceCallActiveAudio) {
            try { voiceCallActiveAudio.pause(); } catch(e) {}
        }
    } else {
        btn.classList.remove('disabled');
        btn.title = "Mute Speaker";
        if (voiceCallActiveAudio && isProgramSpeaking) {
            try { voiceCallActiveAudio.play(); } catch(e) {}
        }
    }
}

function endVoiceCall() {
    isVoiceCallActive = false;
    playHangupSound(); // Play telephone-like disconnect tone
    
    if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
    }
    currentSpeechText = "";
    
    if (voiceCallVisualizerAnimation) {
        cancelAnimationFrame(voiceCallVisualizerAnimation);
        voiceCallVisualizerAnimation = null;
    }
    
    if (voiceCallMicStream) {
        voiceCallMicStream.getTracks().forEach(track => track.stop());
        voiceCallMicStream = null;
    }
    if (voiceCallUserSource) {
        try { voiceCallUserSource.disconnect(); } catch(e) {}
        voiceCallUserSource = null;
    }
    voiceCallUserAnalyser = null;
    
    if (voiceCallActiveAudio) {
        voiceCallActiveAudio.pause();
        voiceCallActiveAudio = null;
    }
    
    if (voiceCallAudioContext) {
        try { voiceCallAudioContext.close(); } catch(e) {}
        voiceCallAudioContext = null;
    }
    voiceCallAnalyser = null;
    
    if (voiceCallRecognition) {
        try { voiceCallRecognition.stop(); } catch(e) {}
        voiceCallRecognition = null;
    }
    
    const overlay = document.getElementById('voice-call-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    
    if (voiceCallTranscript.length > 0) {
        const durationSec = Math.round((Date.now() - voiceCallStartTime) / 1000);
        let durationText = "";
        if (durationSec < 60) {
            durationText = `${durationSec}s`;
        } else {
            const mins = Math.floor(durationSec / 60);
            const secs = durationSec % 60;
            durationText = `${mins}m ${secs}s`;
        }
        
        const payload = {
            duration: durationText,
            turns: voiceCallTranscript
        };
        
        fetch('/api/voice_call/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                transcript: JSON.stringify(payload)
            })
        }).then(res => res.json()).then(data => {
            if (data.success) {
                appendMessage('voice-call', JSON.stringify(payload), null, null, true, Date.now() / 1000);
            }
        }).catch(err => {
            console.error("Error saving voice call transcript:", err);
        });
    }
}

let visualizerAmplitude = 5;
function drawVisualizer() {
    if (!isVoiceCallActive) return;
    voiceCallVisualizerAnimation = requestAnimationFrame(drawVisualizer);
    
    let targetAmp = 2;
    let speed = 0.05;
    
    const statusEl = document.getElementById('voice-call-status');
    const currentStatus = statusEl ? statusEl.textContent : "";
    
    if (isProgramSpeaking && !voiceCallSpeakerMuted && voiceCallAnalyser) {
        const bufferLength = voiceCallAnalyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        voiceCallAnalyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
        }
        const avgVolume = sum / bufferLength; // 0 to 255
        targetAmp = Math.max(3, (avgVolume / 255) * 45);
        speed = 0.05 + (avgVolume / 255) * 0.25;
    } else if (isProgramThinking) {
        targetAmp = 4;
        speed = 0.03;
    } else if (isVoiceCallActive && !voiceCallMuted && currentStatus === "Listening...") {
        let userVolume = 0;
        if (voiceCallUserAnalyser) {
            const bufferLength = voiceCallUserAnalyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            voiceCallUserAnalyser.getByteFrequencyData(dataArray);
            
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            userVolume = sum / bufferLength; // 0 to 255
        }
        
        if (userVolume > 15) { // User is actively speaking
            targetAmp = Math.max(5, (userVolume / 120) * 25);
            speed = 0.06 + (userVolume / 120) * 0.12;
            lastUserSpeechTime = Date.now();
        } else if (Date.now() - lastUserSpeechTime < 800) {
            targetAmp = 3;
            speed = 0.04;
        } else {
            targetAmp = 1;
            speed = 0.02;
        }
    } else {
        targetAmp = 1;
        speed = 0.01;
    }
    
    visualizerAmplitude += (targetAmp - visualizerAmplitude) * 0.15;
    
    const ring1 = document.querySelector('.voice-call-pulse-ring.ring1');
    const ring2 = document.querySelector('.voice-call-pulse-ring.ring2');
    const avatar = document.getElementById('voice-call-program-avatar');
    
    if (ring1 && ring2) {
        let scaleVal1 = 1.0;
        let opacityVal1 = 0.0;
        let scaleVal2 = 1.0;
        let opacityVal2 = 0.0;
        
        if (isProgramSpeaking) {
            // Audio reactive ring pulses + avatar pulsing size (slightly tighter scale)
            const scaleFactor = 1.0 + (visualizerAmplitude / 45) * 0.45;
            const timeScale1 = (Date.now() / 800) % 2.0; // cycle 0 to 2
            const timeScale2 = ((Date.now() + 800) / 800) % 2.0;
            
            scaleVal1 = 1.0 + timeScale1 * 0.26 * scaleFactor;
            opacityVal1 = Math.max(0, 0.85 - timeScale1 * 0.45);
            
            scaleVal2 = 1.0 + timeScale2 * 0.26 * scaleFactor;
            opacityVal2 = Math.max(0, 0.85 - timeScale2 * 0.45);
            
            if (avatar) {
                avatar.style.transform = `scale(${1.0 + (visualizerAmplitude / 45) * 0.07})`;
            }
        } else if (isProgramThinking) {
            // Rapid circular breath wave for thinking
            const timeVal = Date.now() / 200;
            scaleVal1 = 1.04 + Math.sin(timeVal) * 0.08;
            opacityVal1 = 0.6 + Math.sin(timeVal) * 0.15;
            
            scaleVal2 = 1.04 + Math.cos(timeVal) * 0.08;
            opacityVal2 = 0.4 + Math.cos(timeVal) * 0.15;
            
            if (avatar) {
                avatar.style.transform = 'scale(1)';
            }
        } else if (currentStatus === "Listening...") {
            if (Date.now() - lastUserSpeechTime < 800) {
                // Dynamic reactive visualizer scaling when user actively talks (based on mic volume!)
                const pulseScale = 1.05 + (visualizerAmplitude / 25) * 0.22;
                scaleVal1 = pulseScale;
                opacityVal1 = 0.75;
                scaleVal2 = pulseScale * 1.15;
                opacityVal2 = 0.35;
                
                if (avatar) {
                    avatar.style.transform = `scale(${1.0 + (visualizerAmplitude / 25) * 0.05})`;
                }
            } else {
                // Gentle resting breath pattern (kept inside the frame bounds)
                const timeVal = Date.now() / 1500;
                scaleVal1 = 1.0 + (Math.sin(timeVal) + 1.0) * 0.08;
                opacityVal1 = 0.25 + (Math.sin(timeVal) + 1.0) * 0.08;
                
                scaleVal2 = 1.0 + (Math.cos(timeVal) + 1.0) * 0.08;
                opacityVal2 = 0.15 + (Math.cos(timeVal) + 1.0) * 0.08;
                
                if (avatar) {
                    avatar.style.transform = 'scale(1)';
                }
            }
        } else {
            if (avatar) {
                avatar.style.transform = 'scale(1)';
            }
        }
        
        // Override default CSS animations with dynamic JS calculations
        ring1.style.animation = 'none';
        ring2.style.animation = 'none';
        
        ring1.style.transform = `scale(${scaleVal1})`;
        ring1.style.opacity = opacityVal1;
        
        ring2.style.transform = `scale(${scaleVal2})`;
        ring2.style.opacity = opacityVal2;
    }
}

// Global error handler to replace missing/deleted portraits with a clean placeholder
document.addEventListener('error', function (event) {
    if (event.target.tagName.toLowerCase() === 'img') {
        const src = event.target.src;
        if (src && src.includes('/images/portraits/')) {
            const parent = event.target.parentElement;
            if (parent && parent.classList.contains('message-image-container')) {
                const placeholder = document.createElement('div');
                placeholder.className = 'deleted-image-placeholder';
                placeholder.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px; display: inline-block; vertical-align: middle;">
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                        <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34"></path>
                        <circle cx="12" cy="13" r="4"></circle>
                    </svg>
                    <span>[Portrait Deleted]</span>
                `;
                parent.replaceChild(placeholder, event.target);
            }
        }
    }
}, true);
