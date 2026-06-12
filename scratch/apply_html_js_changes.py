import os
import sys

html_path = "scanner/templates/scanner/index.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Normalize CRLF to LF
html = html.replace("\r\n", "\n")

# 1. Modify onChipInput
on_chip_input_old = """    function onChipInput(input) {
      const val = input.value.trim().toUpperCase();
      const sugBox = document.getElementById('SGB');

      if (!val) {
        sugBox.classList.remove('s');
        return;
      }"""

on_chip_input_new = """    function onChipInput(input) {
      const val = input.value.trim().toUpperCase();
      const sugBox = document.getElementById('SGB');

      if (!val) {
        sugBox.classList.remove('s');
        const ncCard = document.getElementById('ncFlowCard');
        if (ncCard) ncCard.style.display = 'none';
        const techCard = document.getElementById('techApprovalCard');
        if (techCard) techCard.style.display = 'none';
        return;
      }"""

html = html.replace(on_chip_input_old, on_chip_input_new)
print("Updated onChipInput.")

# 2. Modify onCorrectionInput
on_corr_input_old = """    function onCorrectionInput(input) {
      const correctedVal = input.value.trim().toUpperCase();
      if (correctedVal.length >= 5) {"""

on_corr_input_new = """    function onCorrectionInput(input) {
      const correctedVal = input.value.trim().toUpperCase();
      if (!correctedVal) {
        const ncCard = document.getElementById('ncFlowCard');
        if (ncCard) ncCard.style.display = 'none';
        const techCard = document.getElementById('techApprovalCard');
        if (techCard) techCard.style.display = 'none';
      }
      if (correctedVal.length >= 5) {"""

html = html.replace(on_corr_input_old, on_corr_input_new)
print("Updated onCorrectionInput.")

# 3. Modify saveAsNonCodeDirect
save_nc_direct_old = """    function saveAsNonCodeDirect() {
      if (!currentCheckCode) return;

      const grade = selectedNcGrade;
      const type = selectedNcType;

      const payload = {
        code: currentCheckCode,
        grade: grade,
        size: selectedNcGb,
        type: type,
        status: selectedNcStatus, // Required selection classification
        note: 'Saved as non-code entry'
      };

      try {
        const res = await fetch('/api/chips/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify(payload)
        });"""

save_nc_direct_new = """    async function saveAsNonCodeDirect() {
      if (!currentCheckCode) return;

      let valid = true;
      const gbSelector = document.getElementById('ncGbSelector');
      const typeSelector = document.getElementById('ncTypeSelector');
      const classSelector = document.getElementById('ncClassificationSelector');

      if (!selectedNcGb) {
        if (gbSelector) gbSelector.classList.add('invalid-field');
        valid = false;
      } else {
        if (gbSelector) gbSelector.classList.remove('invalid-field');
      }

      if (!selectedNcType) {
        if (typeSelector) typeSelector.classList.add('invalid-field');
        valid = false;
      } else {
        if (typeSelector) typeSelector.classList.remove('invalid-field');
      }

      if (!selectedNcStatus) {
        if (classSelector) classSelector.classList.add('invalid-field');
        valid = false;
      } else {
        if (classSelector) classSelector.classList.remove('invalid-field');
      }

      if (!valid) {
        showToast("Please select all required fields highlighted in red.", true);
        return;
      }

      const grade = selectedNcGrade;
      const type = selectedNcType;

      const payload = {
        code: currentCheckCode,
        grade: grade,
        size: selectedNcGb,
        type: type,
        status: selectedNcStatus,
        note: 'Saved as non-code entry'
      };

      let fetchOpts;
      if (ncChipImageFile) {
        const fd = new FormData();
        Object.entries(payload).forEach(([k, v]) => fd.append(k, v));
        fd.append('image', ncChipImageFile, ncChipImageFile.name);
        fetchOpts = { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() }, body: fd };
      } else {
        fetchOpts = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify(payload)
        };
      }

      try {
        const res = await fetch('/api/chips/', fetchOpts);"""

html = html.replace(save_nc_direct_old, save_nc_direct_new)
print("Updated saveAsNonCodeDirect.")

# 4. Modify checkChip display logic
check_chip_old = """      sugBox.classList.remove('s');
      errCard.classList.remove('s');
      resultCard.classList.remove('s');
      ncCard.style.display = 'none';
      corrRow.style.display = 'none';"""

check_chip_new = """      sugBox.classList.remove('s');
      errCard.classList.remove('s');
      resultCard.classList.remove('s');
      if (ncCard) ncCard.style.display = 'none';
      const techCard = document.getElementById('techApprovalCard');
      if (techCard) techCard.style.display = 'none';
      corrRow.style.display = 'none';"""

html = html.replace(check_chip_old, check_chip_new)

check_chip_display_old = """        // Auto-select in UI
        const gradeSelector = document.getElementById('ncGradeSelector');
        if (gradeSelector) {
          const btn = Array.from(gradeSelector.querySelectorAll('.ptab')).find(b => b.textContent.includes(defaultGrade));
          if (btn) setNcGrade(defaultGrade, btn);
        }
        const typeSelector = document.getElementById('ncTypeSelector');
        if (typeSelector) {
          const btn = Array.from(typeSelector.querySelectorAll('.ptab')).find(b => b.textContent.includes(defaultType));
          if (btn) setNcType(defaultType, btn);
        }
        ncCard.style.display = 'block';"""

check_chip_display_new = """        resetNcFlowCard();
        if (currentUser && currentUser.role === 'admin') {
          ncCard.style.display = 'block';
        } else {
          const techCard = document.getElementById('techApprovalCard');
          if (techCard) {
            techCard.style.display = 'block';
            document.getElementById('techApprovalCode').textContent = code;
          }
          submitApprovalRequest(code);
        }"""

html = html.replace(check_chip_display_old, check_chip_display_new)
print("Updated checkChip display logic.")

# 5. Modify executeCroppedScan display logic
exec_crop_display_old = """                    const gradeSelector = document.getElementById('ncGradeSelector');
                    if (gradeSelector) {
                      const btn = Array.from(gradeSelector.querySelectorAll('.ptab')).find(b => b.textContent.includes(defaultGrade));
                      if (btn) setNcGrade(defaultGrade, btn);
                    }
                    const typeSelector = document.getElementById('ncTypeSelector');
                    if (typeSelector) {
                      const btn = Array.from(typeSelector.querySelectorAll('.ptab')).find(b => b.textContent.includes(defaultType));
                      if (btn) setNcType(defaultType, btn);
                    }
                    ncCard.style.display = 'block';
                  } else {
                    ncCard.style.display = 'none';
                  }"""

exec_crop_display_new = """                    resetNcFlowCard();
                    if (currentUser && currentUser.role === 'admin') {
                      ncCard.style.display = 'block';
                    } else {
                      const techCard = document.getElementById('techApprovalCard');
                      if (techCard) {
                        techCard.style.display = 'block';
                        document.getElementById('techApprovalCode').textContent = resObj.chip_code;
                      }
                      submitApprovalRequest(resObj.chip_code);
                    }
                  } else {
                    ncCard.style.display = 'none';
                    const techCard = document.getElementById('techApprovalCard');
                    if (techCard) techCard.style.display = 'none';
                  }"""

html = html.replace(exec_crop_display_old, exec_crop_display_new)
print("Updated executeCroppedScan display logic.")

# 6. Modify loginSuccess role logic
login_success_old = """      if (user.role === 'admin') {
        uc.classList.add('adm');
        udp.classList.add('ap');
        document.getElementById('nb-admin').style.display = 'flex';
      } else {
        uc.classList.remove('adm');
        udp.classList.remove('ap');
        document.getElementById('nb-admin').style.display = 'none';
      }"""

login_success_new = """      if (user.role === 'admin') {
        uc.classList.add('adm');
        udp.classList.add('ap');
        document.getElementById('nb-admin').style.display = 'flex';
        document.getElementById('nb-manual').style.display = 'flex';
      } else {
        uc.classList.remove('adm');
        udp.classList.remove('ap');
        document.getElementById('nb-admin').style.display = 'none';
        document.getElementById('nb-manual').style.display = 'none';
      }
      fetchNotifications();"""

html = html.replace(login_success_old, login_success_new)
print("Updated loginSuccess.")

# 7. Modify goTab
go_tab_old = """    function goTab(tabName) {
      currentTab = tabName;"""

go_tab_new = """    function goTab(tabName) {
      if (tabName === 'manual' && (!currentUser || currentUser.role !== 'admin')) {
        showToast("Access Denied: Admin role required for the Add module.", true);
        return;
      }
      currentTab = tabName;"""

html = html.replace(go_tab_old, go_tab_new)
print("Updated goTab tab access block.")

with open(html_path, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(html)
print("index.html JS changes applied successfully!")
