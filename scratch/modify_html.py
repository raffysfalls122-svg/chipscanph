with open("scanner/templates/scanner/index.html", "r", encoding="utf-8") as f:
    text = f.read()

helpers_and_submit = r'''    async function readScanStream(response, onEvent, onDone, onError) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // keep last incomplete line
          
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) {
              try {
                const parsed = JSON.parse(trimmed);
                onEvent(parsed);
              } catch (e) {
                console.error("JSON parse error on line:", trimmed, e);
              }
            }
          }
        }
        if (buffer.trim()) {
          try {
            const parsed = JSON.parse(buffer.trim());
            onEvent(parsed);
          } catch (e) {}
        }
        onDone();
      } catch (err) {
        onError(err);
      }
    }

    function handleLiveScanStreamEvent(data) {
      const event = data.event;
      if (event === 'started') {
        // Overlay reset already done in openScanLive()
      } else if (event === 'image_match') {
        const imageFound = !!data.image_found;
        const imageCode = data.image_code || '';
        
        const imgStep = document.getElementById('slStepImg');
        imgStep.classList.add('on');
        document.getElementById('slImgSpin').style.display = 'none';
        document.getElementById('slImgDetail').classList.add('show');
        const is = document.getElementById('slImgStatus');
        is.innerHTML = imageFound
          ? 'Image Match <span class="sl-ok">✅ Found</span>' + (imageCode ? ' — ' + imageCode : '')
          : 'Image Match <span class="sl-no">❌ Not Found</span>';
          
      } else if (event === 'text_match') {
        const textFound = !!data.text_found;
        const textCode = data.text_code || '';
        
        document.getElementById('slTextSpin').style.display = 'none';
        document.getElementById('slTextDetail').classList.add('show');
        document.getElementById('slTextCode').textContent = (textCode && textCode !== 'Unknown') ? textCode : '(unreadable)';
        const ts = document.getElementById('slTextStatus');
        ts.innerHTML = textFound ? 'Text Match <span class="sl-ok">✅ Found</span>' : 'Text Match <span class="sl-no">❌ Not Found</span>';
        
        // As text match completes, show image spinner if visual search is still active
        if (document.getElementById('slImgSpin').style.display !== 'none' && !document.getElementById('slImgDetail').classList.contains('show')) {
          document.getElementById('slImgSpin').style.display = 'inline-block';
        }
      } else if (event === 'ai_started') {
        document.getElementById('slTextHdr').textContent = '🔍 Consulting AI Vision…';
        document.getElementById('slTextSpin').style.display = 'inline-block';
      } else if (event === 'final_result') {
        const finalFound = !!data.found;
        document.getElementById('slDivider').style.display = 'block';
        document.getElementById('slResult').classList.add('show');
        if (finalFound) {
          renderScanResultCard(data);
        } else {
          renderScanNotFound();
        }
      }
    }

    function handleCropScanStreamEvent(data) {
      const event = data.event;
      if (event === 'started') {
        // Reset done in executeCroppedScan()
      } else if (event === 'image_match') {
        const imageFound = !!data.image_found;
        const imageCode = data.image_code || '';
        
        document.getElementById('spImgSpin').style.display = 'none';
        document.getElementById('spImgResult').style.display = 'block';
        const is = document.getElementById('spImgStatus');
        is.textContent = imageFound
          ? `✅ Image Match Found${imageCode ? ' — ' + imageCode : ''}`
          : '❌ Image Match Not Found';
        is.style.color = imageFound ? 'var(--g5)' : 'var(--g1)';
        
      } else if (event === 'text_match') {
        const textFound = !!data.text_found;
        const textCode = data.text_code || '';
        
        document.getElementById('spTextSpin').style.display = 'none';
        document.getElementById('spTextResult').style.display = 'block';
        document.getElementById('spTextCode').textContent = textCode && textCode !== 'Unknown' ? textCode : '(unreadable)';
        const ts = document.getElementById('spTextStatus');
        ts.textContent = textFound ? '✅ Text Match Found' : '❌ Text Match Not Found';
        ts.style.color = textFound ? 'var(--g5)' : 'var(--g1)';
        
        // Show image spinner if still running
        if (document.getElementById('spImgSpin').style.display !== 'none' && document.getElementById('spImgResult').style.display !== 'block') {
          document.getElementById('spImgSpin').style.display = 'inline-block';
        }
      } else if (event === 'ai_started') {
        document.getElementById('spTextTitle').textContent = '🔤 Consulting AI Vision…';
        document.getElementById('spTextSpin').style.display = 'inline-block';
      } else if (event === 'final_result') {
        const finalFound = !!data.found;
        const fin = document.getElementById('spFinal');
        const body = document.getElementById('spFinalBody');
        fin.style.display = 'block';
        
        const chip = data.chip || (data.result && data.result.matched ? data.result : null);
        if (finalFound && chip) {
          const g = chip.grade || (data.result && data.result.grade) || '—';
          const gName = (GRADES_INFO[g] || { name: g }).name;
          const code = chip.code || data.code || data.text_code || '';
          body.innerHTML = `
            <div style="font-family:monospace; line-height:1.9">
              <div>Code: <b>${code}</b></div>
              <div>Grade: <b>${gName} (${g})</b></div>
              <div>Storage: <b>${chip.size || '—'}</b></div>
              <div>Type: <b>${chip.type || '—'}</b></div>
              <div>Classification: <b>${(chip.status || '') === 'coded' ? '🔐 Coded' : '📦 Non-Coded'}</b></div>
            </div>`;
        } else {
          body.innerHTML = `
            <div style="color:var(--g2); line-height:1.7">
              ⚠️ Code not found in database by text or image.<br>
              Add it manually below so future scans recognize it.
            </div>`;
        }

        // Set the AI status note
        const aiNoteEl = document.getElementById('aiScanNote');
        if (aiNoteEl) {
          if (data.ai_message) {
            aiNoteEl.textContent = data.ai_message;
          } else if (data.ai_status === 'active') {
            aiNoteEl.textContent = "AI-assisted extraction only. Final chip details are verified from the database.";
          } else if (data.ai_status === 'disabled') {
            aiNoteEl.textContent = "AI assistance disabled. Using OCR-only matching.";
          } else if (data.ai_status === 'unavailable') {
            aiNoteEl.textContent = "AI model unavailable. Check OPENROUTER_MODEL. Using OCR-only matching.";
          } else if (data.ai_status === 'failed_json') {
            aiNoteEl.textContent = "AI returned invalid response. Using OCR-only matching.";
          } else {
            aiNoteEl.textContent = "AI request failed. Using OCR-only matching.";
          }
        }
      }
    }

    // Open the live overlay, POST the photo, then read the real-time stream response
    function submitScanBlob(blob, filename) {
      console.log('[SUBMIT] Submitting scan blob:', filename, 'Size:', blob.size);

      // Show loading animation immediately
      openScanLive();

      const fd = new FormData();
      fd.append('image', blob, filename);
      if (currentUser) fd.append('user', currentUser.username);

      console.log('[SUBMIT] POST /api/scan/image/ with blob size:', blob.size);

      fetch('/api/scan/image/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: fd
      })
        .then(async response => {
          console.log('[SUBMIT] Response status:', response.status);
          if (!response.ok) throw new Error('HTTP ' + response.status);
          
          let lastData = null;
          await readScanStream(
            response,
            (eventData) => {
              console.log('[STREAM EVENT]', eventData);
              handleLiveScanStreamEvent(eventData);
              if (eventData.event === 'final_result') {
                lastData = eventData;
              }
            },
            () => {
              console.log('[STREAM DONE]');
              // Play scan chime if matched
              if (lastData && lastData.found) {
                playScanChime();
              }
            },
            (err) => {
              console.error('[STREAM ERROR]', err);
              showToast('❌ Scan failed: ' + err.message, true);
              closeScanLive();
            }
          );
        })
        .catch(err => {
          console.error('[SUBMIT] Network/Parse error:', err.message);
          showToast('❌ Scan failed: ' + err.message, true);
          closeScanLive();
        });
    }'''

execute_cropped_scan_code = r'''    function executeCroppedScan() {
      document.getElementById('CI').value = '';
      document.getElementById('CI_correct').value = '';
      const spPanel = document.getElementById('scanProcess');
      if (spPanel) spPanel.style.display = 'none';

      const canvas = document.getElementById('cropCanvas');
      const finalCanvas = document.createElement('canvas');

      const sourceX = Math.round(cropBox.x * canvas.width);
      const sourceY = Math.round(cropBox.y * canvas.height);
      const sourceW = Math.round(cropBox.w * canvas.width);
      const sourceH = Math.round(cropBox.h * canvas.height);

      finalCanvas.width = sourceW;
      finalCanvas.height = sourceH;

      const ctx = finalCanvas.getContext('2d');
      ctx.drawImage(canvas, sourceX, sourceY, sourceW, sourceH, 0, 0, sourceW, sourceH);

      closeCropModal();

      // Show the on-page scanProcess panel and update it as stream events arrive
      const panel = document.getElementById('scanProcess');
      panel.style.display = 'block';
      panel.scrollIntoView({ behavior: 'smooth' });

      document.getElementById('spTextSpin').style.display = 'inline-block';
      document.getElementById('spTextResult').style.display = 'none';
      document.getElementById('spImgSpin').style.display = 'none';
      document.getElementById('spImgResult').style.display = 'none';
      document.getElementById('spFinal').style.display = 'none';

      let finalW = sourceW;
      let finalH = sourceH;
      const maxDim = 1000;
      if (finalW > maxDim || finalH > maxDim) {
        if (finalW > finalH) {
          finalH = Math.round((finalH * maxDim) / finalW);
          finalW = maxDim;
        } else {
          finalW = Math.round((finalW * maxDim) / finalH);
          finalH = maxDim;
        }
      }

      const compressedCanvas = document.createElement('canvas');
      compressedCanvas.width = finalW;
      compressedCanvas.height = finalH;
      const compCtx = compressedCanvas.getContext('2d');
      compCtx.drawImage(finalCanvas, 0, 0, finalW, finalH);

      compressedCanvas.toBlob(function (blob) {
        const formData = new FormData();
        formData.append('image', blob, 'cropped_chip.jpg');
        if (currentUser) {
          formData.append('user', currentUser.username);
        }

        fetch('/api/scan/image/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken()
          },
          body: formData
        })
          .then(async response => {
            if (!response.ok) {
              throw new Error("HTTP error " + response.status);
            }
            
            let lastData = null;
            await readScanStream(
              response,
              (eventData) => {
                console.log('[CROP STREAM EVENT]', eventData);
                handleCropScanStreamEvent(eventData);
                if (eventData.event === 'final_result') {
                  lastData = eventData;
                }
              },
              () => {
                console.log('[CROP STREAM DONE]');
                if (lastData && lastData.success && lastData.result) {
                  const resObj = lastData.result;
                  showToast(resObj.matched ? "✓ Scan matched successfully!" : "⚠️ Unknown Chip. Verify code details.");
                  renderResultCard(null, true, resObj);

                  // Set the correction row and input values
                  document.getElementById('ocrCorrectionRow').style.display = 'flex';
                  if (resObj.chip_code === 'Unknown') {
                    document.getElementById('CI_correct').value = '';
                    document.getElementById('CI').value = '';
                    currentCheckCode = '';
                  } else {
                    document.getElementById('CI_correct').value = resObj.chip_code;
                    document.getElementById('CI').value = resObj.chip_code;
                    currentCheckCode = resObj.chip_code;
                  }

                  // Non-code card display
                  const ncCard = document.getElementById('ncFlowCard');
                  if (!resObj.matched) {
                    let defaultGrade = 'A2';
                    let defaultType = 'eMMC';
                    const code = resObj.chip_code.toUpperCase();
                    if (code !== 'UNKNOWN') {
                      if (code.startsWith('KM8') || code.startsWith('H9HQ')) {
                        defaultGrade = 'A5';
                      } else if (code.startsWith('KM5') || code.startsWith('KM3')) {
                        defaultGrade = 'A4';
                      } else if (code.startsWith('TYD') || code.startsWith('TYE')) {
                        defaultGrade = 'A2';
                        defaultType = 'eMCP';
                      }
                    }
                    
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
                    ncCard.style.display = 'block';
                  } else {
                    ncCard.style.display = 'none';
                  }
                }
              },
              (err) => {
                showToast("Scan failed: " + err.message, true);
              }
            );
          })
          .catch(err => {
            showToast("Scan failed: " + err.message, true);
          });
      }, 'image/jpeg', 0.8);
    }'''

# Replace submitScanBlob
submit_start = text.find("    // Open the live overlay, POST the photo, then animate the two-step result")
submit_end = text.find("    function openScanLive() {")

if submit_start != -1 and submit_end != -1:
    text = text[:submit_start] + helpers_and_submit + "\n\n" + text[submit_end:]
    print("Submit scan blob replaced successfully!")
else:
    print("Failed to find boundaries for submitScanBlob", submit_start, submit_end)

# Replace executeCroppedScan (since lines shifted, find again)
crop_start = text.find("    function executeCroppedScan() {")
crop_end = text.rfind("  </script>")

if crop_start != -1 and crop_end != -1:
    text = text[:crop_start] + execute_cropped_scan_code + "\n  " + text[crop_end:]
    print("executeCroppedScan replaced successfully!")
else:
    print("Failed to find boundaries for executeCroppedScan", crop_start, crop_end)

with open("scanner/templates/scanner/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("HTML modification completed!")
