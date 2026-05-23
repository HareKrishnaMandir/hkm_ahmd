// Copyright (c) 2026, Hare Krishna Movement Ahmedabad and contributors
// For license information, please see license.txt

// frappe.ui.form.on("TM Task", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2025, HKM Ahmedabad and contributors
// For license information, please see license.txt

let td_timer_interval = null;
const TD_MAX_SECONDS = 4 * 60 * 60; // 4 hours

function formatHMS(totalSeconds) {
  totalSeconds = Math.max(0, Math.floor(totalSeconds));
  const h = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function elapsedSeconds(from_time) {
  if (!from_time) return 0;
  try {
    const started = new Date(from_time);
    const now = new Date();
    if (isNaN(started.getTime())) {
      console.error("Invalid from_time:", from_time);
      return 0;
    }
    return Math.max(0, Math.floor((now - started) / 1000));
  } catch (e) {
    console.error("Error calculating elapsed seconds:", e);
    return 0;
  }
}

/* ── Pause state persistence (survives refresh) ────────────── */
function _pauseKey(frm) {
  return `td_timer_paused__${frm.doc.name}`;
}

function _savePausedState(frm) {
  localStorage.setItem(
    _pauseKey(frm),
    JSON.stringify({
      is_paused: true,
      paused_seconds: frm.__td_paused_seconds || 0,
      activity_type: frm.__td_activity_type || "",
    })
  );
}

function _clearPausedState(frm) {
  localStorage.removeItem(_pauseKey(frm));
}

function _loadPausedState(frm) {
  try {
    const raw = localStorage.getItem(_pauseKey(frm));
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data.is_paused) return false;
    frm.__td_is_paused      = true;
    frm.__td_paused_seconds = data.paused_seconds || 0;
    frm.__td_activity_type  = data.activity_type  || "";
    return true;
  } catch (e) {
    return false;
  }
}

/* ── Inject CSS once ───────────────────────────────────────── */
function _injectTimerCSS() {
  if (document.getElementById("td-timer-style")) return;
  const style = document.createElement("style");
  style.id = "td-timer-style";
  style.textContent = `
    .td-timer-wrap {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 10px;
      border-radius: 4px;
      background: rgba(0,0,0,0.06);
      font-variant-numeric: tabular-nums;
      font-weight: 700;
      font-size: 12px;
      white-space: nowrap;
      border: 1px solid rgba(0,0,0,0.1);
      letter-spacing: 0.3px;
      transition: background 0.3s, color 0.3s;
      flex-shrink: 0;
    }

    /* Desktop: badge inline in title area */
    .td-timer-inline {
      display: inline-flex;
      margin-left: 8px;
      vertical-align: middle;
    }

    /* Mobile: badge in its own bar below page-head */
    .td-timer-bar {
      display: none;
      align-items: center;
      padding: 3px 12px 4px;
      background: #fff;
      border-bottom: 1px solid var(--border-color, #e2e6e9);
    }

    @media (min-width: 768px) {
      .td-timer-inline { display: inline-flex; }
      .td-timer-bar    { display: none !important; }
    }

    @media (max-width: 767px) {
      .td-timer-inline { display: none !important; }
      .td-timer-bar    { display: flex; }
    }
  `;
  document.head.appendChild(style);
}

/* ── Build timer elements (called once) ────────────────────── */
function ensureHeaderTimer(frm) {
  _injectTimerCSS();

  const wrapper = $(frm.page.wrapper);
  if (wrapper.find(".td-timer-wrap").length) return;

  const wrap = $(`
    <div class="td-timer-wrap">
      <span class="td-timer-icon">⏱</span>
      <span class="td-timer">00:00:00</span>
    </div>
  `);

  // Desktop clone — inside title-area
  const desktopWrap = wrap.clone(true);
  desktopWrap.addClass("td-timer-inline");
  const titleArea = wrapper.find(".page-head .title-area");
  if (titleArea.length) titleArea.append(desktopWrap);

  // Mobile clone — in a bar below page-head
  const mobileWrap = wrap.clone(true);
  const bar = $(`<div class="td-timer-bar"></div>`);
  bar.append(mobileWrap);
  const pageHead = wrapper.find(".page-head");
  if (pageHead.length) pageHead.after(bar);

  frm.__td_timer_els   = wrapper.find(".td-timer");
  frm.__td_timer_wraps = wrapper.find(".td-timer-wrap");
  frm.__td_timer_bar   = bar;
}

function setTimerText(frm, seconds) {
  if (frm.__td_timer_els && frm.__td_timer_els.length) {
    frm.__td_timer_els.text(formatHMS(seconds));
  }
}

function setTimerBadgeState(frm, state) {
  if (!frm.__td_timer_wraps || !frm.__td_timer_wraps.length) return;

  const themes = {
    idle:    { bg: "rgba(0,0,0,0.06)",        color: "",        icon: "⏱" },
    running: { bg: "rgba(34, 197, 94, 0.15)",  color: "#15803d", icon: "▶" },
    paused:  { bg: "rgba(245, 158, 11, 0.15)", color: "#b45309", icon: "⏸" },
  };

  const t = themes[state] || themes.idle;
  frm.__td_timer_wraps.css({ background: t.bg, color: t.color });
  frm.__td_timer_wraps.find(".td-timer-icon").text(t.icon);
}

/* ── Local tick ────────────────────────────────────────────── */
function stopLocalTimer() {
  if (td_timer_interval) clearInterval(td_timer_interval);
  td_timer_interval = null;
}

function startLocalTimer(frm, startSeconds) {
  stopLocalTimer();
  let seconds = Math.max(0, Math.floor(startSeconds || 0));
  frm.__td_local_seconds = seconds;
  setTimerText(frm, seconds);

  td_timer_interval = setInterval(async () => {
    seconds += 1;
    frm.__td_local_seconds = seconds;
    setTimerText(frm, seconds);

    if (seconds >= 14400) {
      stopLocalTimer(); 
      await _autoStopTimer(frm); 
    }
  }, 1000);
}

/* ── Auto-stop handler ─────────────────────────────────────── */
async function _autoStopTimer(frm) {
  try {
    // 1. Call the backend to finalize the 4-hour cap
    const res = await frappe.call({
      method: "hkm_ahmd.project_management.doctype.tm_task.tm_task.stop_timer",
      args: { 
        task: frm.doc.name,
        paused_seconds: 0 
      },
    });

    const recorded_hrs = res.message?.hours || 4.0;

    _resetTimerState(frm);

    await frm.reload_doc();
    setTimeout(() => render_timer_state(frm), 200);

    frappe.msgprint({
      title: __('⏱ Timer Hard Limit Reached'),
      indicator: 'orange',
      message: `
        <div style="text-align: center; padding: 10px;">
          <div style="font-size: 40px; margin-bottom: 10px;">⌛</div>
          <p>Your timer for <b>${frm.doc.title || frm.doc.name}</b> has reached the maximum limit of <b>4 hours</b>.</p>
          <hr>
          <p style="font-size: 0.9em; color: var(--text-muted);">
            The system has automatically recorded <b>${recorded_hrs} hrs</b> to your timesheet.
          </p>
          <p><b>Please start a new timer if you are still working on this task.</b></p>
        </div>
      `,
      primary_action: {
        label: __('Understood'),
        action(values) {
        }
      }
    });

  } catch (e) {
    console.error("Auto-stop failed:", e);
    frappe.show_alert({ 
      message: __("Timer auto-stop failed. Please stop manually."), 
      indicator: "red" 
    });
  }
}

/* ── Button colour helper ──────────────────────────────────── */
function styleBtn(btn, color) {
  const palette = {
    green: { bg: "#16a34a", hover: "#15803d" },
    amber: { bg: "#d97706", hover: "#b45309" },
    red:   { bg: "#dc2626", hover: "#b91c1c" },
  };
  const p = palette[color];
  if (!p || !btn || !btn.length) return;

  btn.css({
    "background-color": p.bg,
    color: "#fff",
    border: "none",
    "border-radius": "6px",
    "font-weight": "600",
    transition: "background-color 0.2s",
  });
  btn.off("mouseenter mouseleave");
  btn.on("mouseenter", () => btn.css("background-color", p.hover));
  btn.on("mouseleave", () => btn.css("background-color", p.bg));
}

function applyButtonColors(frm) {
  setTimeout(() => {
    $(frm.page.wrapper).find(".btn").each(function () {
      const text = $(this).text().trim();
      if      (text === "Start Timer")  styleBtn($(this), "green");
      else if (text === "Pause Timer")  styleBtn($(this), "amber");
      else if (text === "Resume Timer") styleBtn($(this), "green");
      else if (text === "End Timer")    styleBtn($(this), "red");
    });
  }, 120);
}

/* ── Button group helpers ──────────────────────────────────── */
function clearTimerGroup(frm) {
  frm.remove_custom_button("Start Timer",  "Timer");
  frm.remove_custom_button("Pause Timer",  "Timer");
  frm.remove_custom_button("Resume Timer", "Timer");
  frm.remove_custom_button("End Timer",    "Timer");
}

/* ── STATE: idle → show only Start ────────────────────────── */
function showIdleButtons(frm) {
  clearTimerGroup(frm);

  frm.add_custom_button("Start Timer", () => {
    const d = new frappe.ui.Dialog({
      title: "Start Timer",
      fields: [
        {
          fieldname: "activity_type",
          label: "Activity Type",
          fieldtype: "Data",
          reqd: 1,
        },
      ],
      primary_action_label: "Start",
      primary_action: async (v) => {
        await frappe.call({
          method: "hkm_ahmd.project_management.doctype.tm_task.tm_task.start_timer",
          args: { task: frm.doc.name, activity_type: v.activity_type },
        });

        d.hide();
        frappe.show_alert({ message: "Timer started", indicator: "green" });

        frm.__td_activity_type  = v.activity_type;
        frm.__td_paused_seconds = 0;
        frm.__td_is_paused      = false;

        await frm.reload_doc();
        setTimeout(() => render_timer_state(frm), 200);
      },
    });
    d.show();
  }, "Timer");

  applyButtonColors(frm);
}

/* ── STATE: running → show Pause + End ────────────────────── */
function showRunningButtons(frm) {
  clearTimerGroup(frm);

  // frm.add_custom_button("Pause Timer", () => {
  //   frm.__td_paused_seconds = frm.__td_local_seconds || 0;
  //   frm.__td_is_paused      = true;

  //   _savePausedState(frm);

  //   stopLocalTimer();
  //   setTimerText(frm, frm.__td_paused_seconds);
  //   setTimerBadgeState(frm, "paused");

  //   frappe.show_alert({ message: "Timer paused", indicator: "orange" });

  //   showPausedButtons(frm);
  // }, "Timer");

  frm.add_custom_button("End Timer", async () => {
    const res = await frappe.call({
      method: "hkm_ahmd.project_management.doctype.tm_task.tm_task.stop_timer",
      args: { task: frm.doc.name },
    });

    frappe.show_alert({
      message: `Timer stopped. Hours: ${res.message?.hours || 0}`,
      indicator: "blue",
    });

    _resetTimerState(frm);
    await frm.reload_doc();
    setTimeout(() => render_timer_state(frm), 200);
  }, "Timer");

  applyButtonColors(frm);
}

/* ── STATE: paused → show Resume + End ────────────────────── */
function showPausedButtons(frm) {
  clearTimerGroup(frm);

  frm.add_custom_button("Resume Timer", () => {
    frm.__td_is_paused = false;

    _clearPausedState(frm);

    startLocalTimer(frm, frm.__td_paused_seconds || 0);
    setTimerBadgeState(frm, "running");

    frappe.show_alert({ message: "Timer resumed", indicator: "green" });

    showRunningButtons(frm);
  }, "Timer");

  frm.add_custom_button("End Timer", async () => {
    const pausedSecs = frm.__td_paused_seconds || 0;

    const res = await frappe.call({
      method: "hkm_ahmd.project_management.doctype.tm_task.tm_task.stop_timer",
      args: {
        task: frm.doc.name,
        paused_seconds: pausedSecs,
      },
    });

    frappe.show_alert({
      message: `Timer stopped. Hours: ${res.message?.hours || 0}`,
      indicator: "blue",
    });

    _resetTimerState(frm);
    await frm.reload_doc();
    setTimeout(() => render_timer_state(frm), 200);
  }, "Timer");

  applyButtonColors(frm);
}

function _resetTimerState(frm) {
  stopLocalTimer();
  setTimerText(frm, 0);
  setTimerBadgeState(frm, "idle");
  frm.__td_is_paused      = false;
  frm.__td_paused_seconds = 0;
  frm.__td_local_seconds  = 0;
  _clearPausedState(frm);
}

/* ── TM User cache ─────────────────────────────────────────── */
async function get_current_tm_user() {
  if (window.__current_tm_user !== undefined) return window.__current_tm_user;
  try {
    const r = await frappe.db.get_value(
      "TM User",
      { user: frappe.session.user, is_active: 1 },
      "name"
    );
    window.__current_tm_user = r?.message?.name || null;
  } catch (e) {
    console.error("Could not fetch TM User:", e);
    window.__current_tm_user = null;
  }
  return window.__current_tm_user;
}

/* ── Main render ───────────────────────────────────────────── */
async function render_timer_state(frm) {
  if (!frm || !frm.doc || frm.is_new()) return;
  if (frm.__timer_rendering) return;

  frm.__timer_rendering = true;
  try {
    ensureHeaderTimer(frm);

    if (!frm.__td_is_paused) _loadPausedState(frm);

    if (frm.__td_is_paused) {
      setTimerText(frm, frm.__td_paused_seconds || 0);
      setTimerBadgeState(frm, "paused");
      showPausedButtons(frm);
      return;
    }

    const tm_user = await get_current_tm_user();

    const from_doc = () => {
      const rows = frm.doc.timesheet_table || [];
      for (let i = rows.length - 1; i >= 0; i--) {
        const r = rows[i];
        if (r.from_time && !r.to_time && r.user === tm_user) return r.from_time;
      }
      return null;
    };

    let from_time = null;

    try {
      const r = await frappe.call({
        method: "hkm_ahmd.project_management.doctype.tm_task.tm_task.get_running_timer",
        args: { task: frm.doc.name },
      });
      from_time = r.message?.from_time || null;
    } catch (e) {
      console.error("get_running_timer failed:", e);
    }

    if (!from_time) from_time = frm.doc?.__onload?.timer_from_time || null;
    if (!from_time) from_time = from_doc();

    if (from_time) {
      const elapsed = elapsedSeconds(from_time);

      // If already past 4 hours when loading (e.g. left tab open), auto-stop immediately
      if (elapsed >= TD_MAX_SECONDS) {
        await _autoStopTimer(frm);
        return;
      }

      startLocalTimer(frm, elapsed);
      setTimerBadgeState(frm, "running");
      showRunningButtons(frm);
    } else {
      stopLocalTimer();
      setTimerText(frm, 0);
      setTimerBadgeState(frm, "idle");
      showIdleButtons(frm);
    }
  } finally {
    frm.__timer_rendering = false;
  }
}

/* ── Doctype events ────────────────────────────────────────── */
frappe.ui.form.on("TM Task", {
  setup(frm) {
    ensureHeaderTimer(frm);
  },

  refresh(frm) {
    if (frm.is_new()) return;
    window.__current_tm_user = undefined;
    render_timer_state(frm);
  },

  onhide(frm) {
    stopLocalTimer();
    if (frm.__td_timer_bar) {
      frm.__td_timer_bar.remove();
      frm.__td_timer_bar   = null;
      frm.__td_timer_els   = null;
      frm.__td_timer_wraps = null;
    }
  },
});

/* ── SPA route change force-render ────────────────────────── */
(function tasks_timer_force_render() {
  if (window.__tasks_timer_force_render) return;
  window.__tasks_timer_force_render = true;

  const run = () => {
    try {
      if (
        window.cur_frm &&
        cur_frm.doctype === "TM Task" &&
        cur_frm.doc &&
        !cur_frm.is_new()
      ) {
        render_timer_state(cur_frm);
      }
    } catch (e) {}
  };

  frappe.router.on("change", () => setTimeout(run, 50));
  frappe.after_ajax(() => setTimeout(run, 50));
  setTimeout(run, 0);
  setTimeout(run, 250);
})();

// ======================================================
// QUICK ENTRY OVERRIDE
// =====================================================
frappe.after_ajax(function(){
  if (!frappe.ui.form.QuickEntryForm) return;

  const _originalRenderDialog = frappe.ui.form.QuickEntryForm.prototype.render_dialog;

  frappe.ui.form.QuickEntryForm.prototype.render_dialog = function () {
    _originalRenderDialog.apply(this, arguments);

    if( this.doctype !== 'TM Task' ) return;

    const qe = this;

    setTimeout(function () {
            const expectedField = qe.dialog.fields_dict['expected_date'];
            if (expectedField) {
                expectedField.set_description('⚠️ Must be a future date (not today or past).');
            }

            qe.dialog.set_primary_action(__('Save'), function () {

                const expectedDateValue = qe.dialog.get_value('expected_date');

                if (expectedDateValue) {
                    const selectedDate = frappe.datetime.str_to_obj(expectedDateValue);
                    const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
                    if (selectedDate <= today) {
                        frappe.msgprint({
                            title: __('Invalid Expected Date'),
                            message: __('The Expected Date ({0}) cannot be Today or in the Past. Please select a future date.', [expectedDateValue]),
                            indicator: 'red'
                        });
                        return; 
                    }
                }
                qe.insert();
            });

        }, 100);
    };
});