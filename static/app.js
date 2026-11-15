
const form = document.querySelector('#form');
const decision = document.querySelector('#decision');
const expertsBox = document.querySelector('#experts');

const icons = ['◈', '▤', '⌁', '⌕', '◎'];

// ------------------------------------------
// 1. SYNCHRONIZE INPUT RANGE VALUES
// ------------------------------------------

function syncRanges() {
  document.querySelector('#scoreval').textContent =
    form.credit_score.value;

  document.querySelector('#sectorval').textContent =
    form.sector_risk.value + ' / 5';

  document.querySelector('#stabilityval').textContent =
    form.stability.value + ' / 5';

  document.querySelectorAll('.weights input').forEach(input => {
    input.nextElementSibling.textContent =
      Number(input.value).toFixed(1) + '×';
  });
}

form.addEventListener('input', syncRanges);
syncRanges();

// ------------------------------------------
// 2. HELPER FUNCTIONS
// ------------------------------------------

const pct = value =>
  (Number(value) * 100).toFixed(1) + '%';

const safe = value =>
  String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));

// ------------------------------------------
// 3. FORM SUBMISSION
// ------------------------------------------

form.addEventListener('submit', async event => {
  event.preventDefault();

  const fd = new FormData(form);
  const data = {};

  fd.forEach((value, key) => {
    if (key.startsWith('w_')) return;

    data[key] = key === 'name'
      ? value
      : Number(value);
  });

  // Expert weights
  data.expert_weights = {
    credit: Number(fd.get('w_credit')),
    financial: Number(fd.get('w_financial')),
    risk: Number(fd.get('w_risk')),
    fraud: Number(fd.get('w_fraud')),
    economic: Number(fd.get('w_economic'))
  };

  // Loading screen
  decision.innerHTML = `
    <div class="panelhead">
      <span class="step">02 / OUTCOME</span>
      <span class="pill">COMPUTING…</span>
    </div>

    <div class="empty">
      <div class="orbit">↻</div>
      <h2>Combining the<br>evidence.</h2>
    </div>
  `;

  try {

    // Send applicant information to FastAPI
    const response = await fetch('/api/assess', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const errorBody = await response.json();

      throw new Error(
        errorBody.detail?.[0]?.msg ||
        'Please check your inputs'
      );
    }

    const result = await response.json();

    render(result);

  } catch (error) {

    decision.innerHTML = `
      <div class="panelhead">
        <span class="step">ASSESSMENT ERROR</span>
      </div>

      <p>${safe(error.message)}</p>
    `;
  }
});

// ------------------------------------------
// 4. DISPLAY ASSESSMENT RESULTS
// ------------------------------------------

function render(r) {

  const dst = r.dst;

  const color =
    r.color === 'approve'
      ? '#d8f36a'
      : r.color === 'reject'
        ? '#ff9b83'
        : '#f2cf68';

  const label =
    r.decision === 'CONDITIONAL'
      ? 'MANUAL REVIEW'
      : r.decision;

  // ----------------------------------------
  // MAIN DECISION PANEL
  // ----------------------------------------

  decision.innerHTML = `

    <div class="panelhead">
      <span class="step">02 / OUTCOME</span>
      <span class="pill">DST ASSESSMENT COMPLETE</span>
    </div>

    <div class="decision-result">

      <div>
        <span class="tag">
          RECOMMENDATION / ${safe(r.applicant).toUpperCase()}
        </span>

        <h2 style="color:${color}">
          ${label}
        </h2>

        <p>${safe(r.reason)}</p>
      </div>

      <div class="scorebig">
        ${Number(r.overall).toFixed(1)}

        <small style="
          font-size:11px;
          color:#aab09f;
          display:block;
          text-align:right;
          letter-spacing:0
        ">
          BELIEF %
        </small>
      </div>

    </div>

    <!-- MAIN METRICS -->

    <div class="metrics">

      <div class="metric">
        <span>APPROVAL BELIEF</span>
        <b>${pct(dst.belief_approval)}</b>
      </div>

      <div class="metric">
        <span>REJECTION BELIEF</span>
        <b>${pct(dst.belief_rejection)}</b>
      </div>

      <div class="metric">
        <span>DTI PROXY</span>
        <b>${r.dti}%</b>
      </div>

    </div>

    <!-- DST PANEL -->

    <div class="dst-panel">

      <div class="dst-heading">
        <span>DEMPSTER–SHAFER EVIDENCE FUSION</span>
        <span class="dst-chip">5 EXPERTS</span>
      </div>

      <div class="dst-grid">

        <div class="dst-stat">
          <span>APPROVAL PLAUSIBILITY</span>
          <b>${pct(dst.plausibility_approval)}</b>
        </div>

        <div class="dst-stat">
          <span>REJECTION PLAUSIBILITY</span>
          <b>${pct(dst.plausibility_rejection)}</b>
        </div>

        <div class="dst-stat">
          <span>UNCERTAINTY · m(Θ)</span>
          <b>${pct(dst.uncertainty)}</b>
        </div>

        <div class="dst-stat">
          <span>CONFLICT · K</span>
          <b>${pct(dst.conflict)}</b>
        </div>

      </div>

      <!-- LEGEND -->

      <div class="dst-legend">

        <span>
          <i class="dot approval"></i>
          Approval belief
        </span>

        <span>
          <i class="dot rejection"></i>
          Rejection belief
        </span>

        <span>
          <i class="dot uncertain"></i>
          Uncertainty
        </span>

      </div>

      <!-- COMBINED BPA VISUALIZATION -->

      <div
        class="stacked-bar"
        aria-label="Combined belief distribution"
      >

        <i
          class="approval"
          style="width:${dst.belief_approval * 100}%"
        ></i>

        <i
          class="rejection"
          style="width:${dst.belief_rejection * 100}%"
        ></i>

        <i
          class="uncertain"
          style="width:${dst.uncertainty * 100}%"
        ></i>

      </div>

    </div>

    <!-- RECOMMENDED SAFEGUARDS -->

    ${r.conditions.length ? `

      <div style="margin-top:18px">

        <span
          class="tag"
          style="color:#f2cf68;font:10px 'DM Mono'"
        >
          RECOMMENDED SAFEGUARDS
        </span>

        <ul style="
          font-size:11px;
          color:#d0d3c8;
          line-height:1.8;
          padding-left:18px
        ">

          ${r.conditions.map(item =>
            `<li>${safe(item)}</li>`
          ).join('')}

        </ul>

      </div>

    ` : ''}

    <!-- SYSTEM NOTE -->

    <p style="
      font-size:9px;
      color:#92998a;
      margin-top:15px
    ">
      ${safe(r.note)}
    </p>

  `;

  // ----------------------------------------
  // 5. DISPLAY FIVE EXPERT MODULES
  // ----------------------------------------

  expertsBox.innerHTML =

    Object.entries(r.experts).map(
      ([name, expert], index) => `

      <div class="expert expert-dst">

        <div class="avatar">
          ${icons[index] || '◈'}
        </div>

        <div>

          <div class="expert-name">

            ${safe(name)}

            <span class="weight-note">
              · ${Number(expert.weight).toFixed(1)}× influence
            </span>

          </div>

          <div class="expert-reason">
            ${safe(expert.rationale)}
          </div>

          <!-- EXPERT SCORE BAR -->

          <div class="bar">
            <i style="width:${expert.score}%"></i>
          </div>

          <!-- EXPERT BPA VALUES -->

          <div class="bpa-values">

            <span>
              A ${pct(expert.bpa.approval)}
            </span>

            <span>
              R ${pct(expert.bpa.rejection)}
            </span>

            <span>
              Θ ${pct(expert.bpa.uncertainty)}
            </span>

            <span>
              Reliability ${pct(expert.reliability)}
            </span>

          </div>

        </div>

        <div class="expert-score">

          ${expert.score}

          <small>/100</small>

        </div>

      </div>

    `).join('');
}

// ------------------------------------------
// 6. RESET APPLICATION
// ------------------------------------------

document.querySelector('#reset').addEventListener('click', () => {

  form.reset();

  syncRanges();

  decision.innerHTML = `

    <div class="panelhead">
      <span class="step">02 / OUTCOME</span>
      <span class="pill">AWAITING RUN</span>
    </div>

    <div class="empty">

      <div class="orbit">✳</div>

      <h2>
        Your decision<br>starts here.
      </h2>

      <p>
        Adjust the applicant profile, then run the assessment
        to combine five experts' evidence using DST.
      </p>

    </div>

  `;

  expertsBox.innerHTML = `
    <div class="placeholder">
      Expert BPA evidence appears after assessment.
    </div>
  `;

});
