import os
import sys

html_path = "scanner/templates/scanner/index.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Normalize CRLF to LF for consistent replacements
html = html.replace("\r\n", "\n")

# 1. Add CSS styles before </style>
styles = """
    /* 🔔 NOTIFICATION SYSTEM STYLES */
    .notif-btn {
      background: var(--s2);
      border: 1px solid var(--bd2);
      color: var(--t1);
      cursor: pointer;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      padding: 0;
      font-size: 16px;
      transition: background 0.2s, transform 0.1s;
    }
    .notif-btn:hover {
      background: var(--bd2);
    }
    .notif-btn:active {
      transform: scale(0.95);
    }
    .notif-badge {
      position: absolute;
      top: -3px;
      right: -3px;
      background: var(--er);
      color: #fff;
      font-size: 9px;
      font-weight: bold;
      border-radius: 50%;
      min-width: 14px;
      height: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1px;
      border: 1.5px solid var(--bg);
    }
    .notif-panel {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      width: 280px;
      background: var(--bg);
      border: 1px solid var(--bd);
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      display: none;
      flex-direction: column;
      max-height: 350px;
      z-index: 100;
      overflow: hidden;
    }
    .notif-panel.show {
      display: flex;
    }
    .notif-header {
      padding: 10px 14px;
      border-bottom: 1px solid var(--bd);
      font-weight: bold;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--s2);
    }
    .notif-clear-btn {
      background: transparent;
      border: none;
      color: var(--g5);
      cursor: pointer;
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .notif-clear-btn:hover {
      background: var(--bd2);
    }
    .notif-list {
      overflow-y: auto;
      flex: 1;
    }
    .notif-item {
      padding: 10px 14px;
      border-bottom: 1px solid var(--bd2);
      font-size: 11px;
      line-height: 1.4;
      color: var(--t1);
      transition: background 0.15s;
    }
    .notif-item.unread {
      background: var(--s1);
      font-weight: 500;
    }
    .notif-item:hover {
      background: var(--s2);
    }
    .notif-empty {
      padding: 24px;
      text-align: center;
      color: var(--g3);
      font-size: 11px;
    }
    .invalid-field {
      border: 2px solid var(--er) !important;
      background-color: rgba(255, 0, 0, 0.05) !important;
      border-radius: 8px !important;
    }
</style>"""

html = html.replace("</style>", styles, 1)
print("CSS styles injected.")

# 2. Modify #ncFlowCard
# Remove non-code warning tip-tx
tip_tx_to_remove = '<div class="tip-tx" style="margin-bottom:12px; color:var(--g2); font-weight:500">You can add this code because it is not recognized as coded, maybe this is non-code.</div>'
html = html.replace(tip_tx_to_remove, '')
print("Removed non-code warning text.")

# Remove grade selector wrapper
grade_selector_wrapper = """        <div id="ncGradeSelectorWrapper">
          <div class="ml" style="margin-bottom:4px">SELECT GRADE / QUALITY:</div>
          <div class="ptabs" style="margin-bottom:10px" id="ncGradeSelector">
            <button class="ptab a" onclick="setNcGrade('A1', this)">A1 (A+)</button>
            <button class="ptab" onclick="setNcGrade('A2', this)">A2 (A++)</button>
            <button class="ptab" onclick="setNcGrade('A3', this)">A3 (A+++)</button>
            <button class="ptab" onclick="setNcGrade('A4', this)">A4 (A++++)</button>
            <button class="ptab" onclick="setNcGrade('A5', this)">A5 (A+++++)</button>
          </div>
        </div>"""
html = html.replace(grade_selector_wrapper, '')
print("Removed grade selector wrapper.")

# Update classification selector block in ncFlowCard
old_class_selector = """        <!-- Required Coded/Non-Coded selector -->
        <div class="ml" style="margin-bottom:4px">CLASSIFICATION: <span style="color:var(--er)">* REQUIRED</span></div>
        <div class="ptabs" style="margin-bottom:12px">
          <button class="ptab a" id="ncSelCoded" onclick="selectNcStatus('coded')">🔐 Coded</button>
          <button class="ptab" id="ncSelNoncode" onclick="selectNcStatus('noncode')">📦 Non-Coded</button>
        </div>"""

new_class_selector = """        <!-- Required Coded/Non-Coded selector -->
        <div class="ml" style="margin-bottom:4px">CLASSIFICATION: <span style="color:var(--er)">* REQUIRED</span></div>
        <div class="ptabs" style="margin-bottom:12px" id="ncClassificationSelector">
          <button class="ptab" id="ncSelCoded" onclick="selectNcStatus('coded')">🔐 Coded</button>
          <button class="ptab" id="ncSelNoncode" onclick="selectNcStatus('noncode')">📦 Non-Coded</button>
        </div>"""
html = html.replace(old_class_selector, new_class_selector)
print("Updated classification selector block.")

# Remove 'a' (default active) class from ncGbSelector
old_gb_selector = '<button class="ptab a" onclick="setNcGb(\'16GB\', this)">16G</button>'
new_gb_selector = '<button class="ptab" onclick="setNcGb(\'16GB\', this)">16G</button>'
html = html.replace(old_gb_selector, new_gb_selector)

# Remove 'a' (default active) class from ncTypeSelector
old_type_selector = '<button class="ptab a" onclick="setNcType(\'eMMC\', this)">eMMC</button>'
new_type_selector = '<button class="ptab" onclick="setNcType(\'eMMC\', this)">eMMC</button>'
html = html.replace(old_type_selector, new_type_selector)
print("Removed default active state classes from card buttons.")

# Insert reference image upload zone (#ncImageZone) inside #ncFlowCard, right before classification selector
insertion_point = '        <!-- Required Coded/Non-Coded selector -->'
image_zone_html = """        <!-- Reference photo upload area inside shortcut flow (FIX 5) -->
        <div class="mg" style="margin-top: 10px; margin-bottom: 12px;">
          <div class="ml" style="margin-bottom:4px">CHIP PHOTO (FOR IMAGE MATCHING)</div>
          <div class="ref-zone" id="ncImageZone" onclick="document.getElementById('ncImageInput').click()"
            style="aspect-ratio:16/9; min-height:120px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:var(--s1); border:2px dashed var(--bd2); border-radius:14px; cursor:pointer; position:relative; overflow:hidden">
            <span style="font-size:28px" id="ncImageIcon">📷</span>
            <span class="ref-lbl" id="ncImageLbl" style="font-size:10px; color:var(--t2); margin-top:4px; text-align:center; padding:0 12px">Tap to attach a clear photo of this chip's surface</span>
            <img id="ncImagePreview" style="display:none; position:absolute; inset:0; width:100%; height:100%; object-fit:contain; background:var(--bg)">
          </div>
          <input type="file" id="ncImageInput" accept="image/*,.jpg,.jpeg,.png,.gif,.bmp,.webp,.heic,.heif" style="display:none" onchange="handleNcImage(this)">
        </div>

        """
html = html.replace(insertion_point, image_zone_html + insertion_point)
print("Injected ncImageZone.")

# 3. Render #techApprovalCard right below #ncFlowCard
flow_card_end = '        <button class="abtn gn" onclick="saveAsNonCodeDirect()">➕ Save as Reference Entry</button>\n      </div>'
tech_approval_card = """        <button class="abtn gn" onclick="saveAsNonCodeDirect()">➕ Save as Reference Entry</button>
      </div>

      <!-- Technician Approval Notification Card (FIX 8) -->
      <div class="warn-card" id="techApprovalCard" style="display:none; border-color: var(--bd2); background: var(--s1)">
        <div class="warn-title" style="color:var(--g2)">⚠️ Code Not in Database</div>
        <div class="tip-tx" style="margin-bottom:6px; color:var(--g2); font-weight:500">
          This chip model is unrecognized. It has been automatically submitted to the Administrator for approval.
        </div>
        <div style="font-size:11px; font-family:monospace; color:var(--g3)">
          Submitted Code: <b id="techApprovalCode"></b>
        </div>
      </div>"""
html = html.replace(flow_card_end, tech_approval_card)
print("Injected techApprovalCard.")

# 4. Add notification bell and panel to header (.hdr)
header_buttons_old = """      <div class="uc" id="UC">
        <div class="pd" id="UDP"></div><span id="UL">—</span>
      </div>
      <button class="lob" onclick="doLogout()">↩ Out</button>"""

header_buttons_new = """      <!-- Notification bell -->
      <div class="notif-btn-wrapper" style="position: relative; margin-right: 4px;">
        <button class="notif-btn" onclick="toggleNotifPanel(event)">
          🔔<span class="notif-badge" id="notifBadge" style="display:none">0</span>
        </button>
        <!-- Notification dropdown panel -->
        <div class="notif-panel" id="notifPanel">
          <div class="notif-header">
            <span>Notifications</span>
            <button class="notif-clear-btn" onclick="clearNotifications(event)">Mark Read</button>
          </div>
          <div class="notif-list" id="notifList">
            <div class="notif-empty">No new notifications</div>
          </div>
        </div>
      </div>
      <div class="uc" id="UC">
        <div class="pd" id="UDP"></div><span id="UL">—</span>
      </div>
      <button class="lob" onclick="doLogout()">↩ Out</button>"""

html = html.replace(header_buttons_old, header_buttons_new)
print("Injected notification bell in header.")

# 5. Add approvals list container to #pg-admin, before DATABASE CONTROLS
database_controls_old = """      <div class="stl">DATABASE CONTROLS</div>"""
database_controls_new = """      <div class="stl">PENDING APPROVAL REQUESTS</div>
      <div class="admin-sec" style="max-height:300px; overflow-y:auto; margin-bottom:15px">
        <div id="approvalsListContainer">
          <div class="notif-empty">No pending approval requests</div>
        </div>
      </div>

      <div class="stl">DATABASE CONTROLS</div>"""
html = html.replace(database_controls_old, database_controls_new)
print("Injected approvals list section in admin console.")

# 6. Add JS actions before closing </script> tag
js_code = """
    // 🔔 NOTIFICATION ACTIONS
    function toggleNotifPanel(e) {
      if (e) e.stopPropagation();
      const panel = document.getElementById('notifPanel');
      if (!panel) return;
      panel.classList.toggle('show');
      if (panel.classList.contains('show')) {
        fetchNotifications();
      }
    }

    async function fetchNotifications() {
      if (!currentUser) return;
      try {
        const res = await fetch(`/api/notifications/?username=${encodeURIComponent(currentUser.username)}&role=${encodeURIComponent(currentUser.role)}`);
        const data = await res.json();
        renderNotifications(data);
      } catch (err) {
        console.error("Failed to fetch notifications:", err);
      }
    }

    function renderNotifications(notifs) {
      const list = document.getElementById('notifList');
      const badge = document.getElementById('notifBadge');
      if (!list) return;

      list.innerHTML = '';
      const unreadCount = notifs.filter(n => !n.is_read).length;

      if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }

      if (notifs.length === 0) {
        list.innerHTML = '<div class="notif-empty">No notifications</div>';
        return;
      }

      notifs.forEach(n => {
        const div = document.createElement('div');
        div.className = `notif-item ${n.is_read ? '' : 'unread'}`;
        div.textContent = n.message;
        list.appendChild(div);
      });
    }

    async function clearNotifications(e) {
      if (e) e.stopPropagation();
      if (!currentUser) return;
      try {
        const res = await fetch('/api/notifications/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            username: currentUser.username,
            role: currentUser.role
          })
        });
        const data = await res.json();
        if (data.success) {
          fetchNotifications();
        }
      } catch (err) {
        console.error("Failed to clear notifications:", err);
      }
    }

    // Close notifications panel on document click
    document.addEventListener('click', () => {
      const panel = document.getElementById('notifPanel');
      if (panel) panel.classList.remove('show');
    });

    // 📋 ADMIN APPROVALS ACTIONS
    async function fetchPendingApprovals() {
      if (!currentUser || currentUser.role !== 'admin') return;
      try {
        const res = await fetch('/api/approvals/');
        const data = await res.json();
        renderPendingApprovals(data);
      } catch (err) {
        console.error("Failed to fetch pending approvals:", err);
      }
    }

    function renderPendingApprovals(reqs) {
      const container = document.getElementById('approvalsListContainer');
      if (!container) return;

      if (reqs.length === 0) {
        container.innerHTML = '<div class="notif-empty">No pending approval requests</div>';
        return;
      }

      container.innerHTML = '';
      reqs.forEach(req => {
        const card = document.createElement('div');
        card.className = 'approval-card';
        card.style = 'border: 1px solid var(--bd); border-radius: 8px; padding: 12px; margin-bottom: 12px; background: var(--s2);';

        let imgHtml = '';
        if (req.image_url) {
          imgHtml = `<div style="margin: 8px 0;"><img src="${req.image_url}" style="max-height: 120px; border-radius: 4px; object-fit: contain;"></div>`;
        }

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
            <div>Code: <b style="color: var(--g5); font-family: monospace;">${req.code}</b></div>
            <div style="color: var(--g3)">From: ${req.technician}</div>
          </div>
          ${imgHtml}
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px;">
            <div>
              <span style="font-size: 9px; color: var(--g3)">CAPACITY</span>
              <select id="app-size-${req.id}" class="ms" style="width:100%; font-size: 11px; padding: 4px;" onchange="handleApprovalCapacityChange(${req.id})">
                <option value="16GB">16GB</option>
                <option value="32GB">32GB</option>
                <option value="64GB">64GB</option>
                <option value="128GB">128GB</option>
                <option value="256GB">256GB</option>
              </select>
            </div>
            <div>
              <span style="font-size: 9px; color: var(--g3)">GRADE</span>
              <select id="app-grade-${req.id}" class="ms" style="width:100%; font-size: 11px; padding: 4px;">
                <option value="A1">A1 (A+)</option>
                <option value="A2">A2 (A++)</option>
                <option value="A3">A3 (A+++)</option>
                <option value="A4">A4 (A++++)</option>
                <option value="A5">A5 (A+++++)</option>
              </select>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px;">
            <div>
              <span style="font-size: 9px; color: var(--g3)">TYPE</span>
              <select id="app-type-${req.id}" class="ms" style="width:100%; font-size: 11px; padding: 4px;">
                <option value="eMMC">eMMC</option>
                <option value="eMCP">eMCP</option>
              </select>
            </div>
            <div>
              <span style="font-size: 9px; color: var(--g3)">CLASSIFICATION</span>
              <select id="app-status-${req.id}" class="ms" style="width:100%; font-size: 11px; padding: 4px;">
                <option value="coded">🔐 Coded</option>
                <option value="noncode">📦 Non-Coded</option>
              </select>
            </div>
          </div>

          <div style="margin-top: 8px;">
            <span style="font-size: 9px; color: var(--g3)">REFERENCE PHOTO (OPTIONAL)</span>
            <input type="file" id="app-image-${req.id}" accept="image/*" style="font-size: 10px; display: block; margin-top: 2px;">
          </div>

          <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end;">
            <button class="abtn go" style="padding: 4px 12px; font-size: 11px; margin: 0; color: var(--er); border-color: var(--er)" onclick="handleApprovalAction(${req.id}, 'reject')">❌ Reject</button>
            <button class="abtn gn" style="padding: 4px 12px; font-size: 11px; margin: 0;" onclick="handleApprovalAction(${req.id}, 'approve')">✅ Approve</button>
          </div>
        `;
        container.appendChild(card);

        // Pre-select grade based on 16GB default capacity
        handleApprovalCapacityChange(req.id);
      });
    }

    function handleApprovalCapacityChange(reqId) {
      const sizeSel = document.getElementById(`app-size-${reqId}`);
      const gradeSel = document.getElementById(`app-grade-${reqId}`);
      if (sizeSel && gradeSel) {
        const size = sizeSel.value;
        const grade = GRADE_BY_SIZE[size] || 'A1';
        gradeSel.value = grade;
      }
    }

    async function handleApprovalAction(reqId, action) {
      if (!currentUser || currentUser.role !== 'admin') return;

      const fd = new FormData();
      fd.append('action', action);
      fd.append('username', currentUser.username);
      fd.append('role', currentUser.role);

      if (action === 'approve') {
        const size = document.getElementById(`app-size-${reqId}`).value;
        const grade = document.getElementById(`app-grade-${reqId}`).value;
        const type = document.getElementById(`app-type-${reqId}`).value;
        const status = document.getElementById(`app-status-${reqId}`).value;

        fd.append('size', size);
        fd.append('grade', grade);
        fd.append('type', type);
        fd.append('status', status);

        const imgInput = document.getElementById(`app-image-${reqId}`);
        if (imgInput && imgInput.files && imgInput.files[0]) {
          fd.append('image', imgInput.files[0], imgInput.files[0].name);
        }
      }

      try {
        const res = await fetch(`/api/approvals/${reqId}/action/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken()
          },
          body: fd
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message);
          fetchPendingApprovals();
          fetchNotifications();
        } else {
          showToast(data.message, true);
        }
      } catch (err) {
        console.error("Failed to action approval request:", err);
        showToast("Error processing approval request", true);
      }
    }

    // 🖼️ SHORTCUT CARD PHOTO UPLOAD & RE-INIT
    let ncChipImageFile = null;

    function handleNcImage(input) {
      const file = input.files && input.files[0];
      if (!file) return;
      ncChipImageFile = file;
      const reader = new FileReader();
      reader.onload = e => {
        const prev = document.getElementById('ncImagePreview');
        prev.src = e.target.result;
        prev.style.display = 'block';
        document.getElementById('ncImageIcon').style.display = 'none';
        document.getElementById('ncImageLbl').textContent = 'Photo attached ✓ — tap to change';
        document.getElementById('ncImageLbl').style.color = 'var(--g5)';
      };
      reader.readAsDataURL(file);
    }

    function resetNcImage() {
      ncChipImageFile = null;
      const inp = document.getElementById('ncImageInput');
      if (inp) inp.value = '';
      const prev = document.getElementById('ncImagePreview');
      if (prev) { prev.src = ''; prev.style.display = 'none'; }
      const ico = document.getElementById('ncImageIcon');
      if (ico) ico.style.display = 'block';
      const lbl = document.getElementById('ncImageLbl');
      if (lbl) {
        lbl.textContent = 'Tap to attach a clear photo of this chip\'s surface';
        lbl.style.color = 'var(--t2)';
      }
    }

    function resetNcFlowCard() {
      selectedNcGb = null;
      selectedNcType = null;
      selectedNcStatus = null;
      resetNcImage();

      // Remove active classes
      const gbSelector = document.getElementById('ncGbSelector');
      if (gbSelector) {
        gbSelector.classList.remove('invalid-field');
        gbSelector.querySelectorAll('.ptab').forEach(b => b.classList.remove('a'));
      }
      const typeSelector = document.getElementById('ncTypeSelector');
      if (typeSelector) {
        typeSelector.classList.remove('invalid-field');
        typeSelector.querySelectorAll('.ptab').forEach(b => b.classList.remove('a'));
      }
      const classSelector = document.getElementById('ncClassificationSelector');
      if (classSelector) {
        classSelector.classList.remove('invalid-field');
        classSelector.querySelectorAll('.ptab').forEach(b => b.classList.remove('a'));
      }
    }

    async function submitApprovalRequest(code) {
      if (!code) return;
      try {
        const res = await fetch('/api/approvals/submit/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            code: code,
            user: currentUser ? currentUser.username : 'Anonymous'
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast("✓ Unrecognized chip automatically submitted for admin approval.");
        }
      } catch (err) {
        console.error("Failed to submit approval request:", err);
      }
    }

    // Polling notifications
    setInterval(fetchNotifications, 8000);
</script>"""

html = html.replace("</script>", js_code, 1)
print("JavaScript helper functions appended.")

with open(html_path, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(html)
print("index.html updated successfully!")
