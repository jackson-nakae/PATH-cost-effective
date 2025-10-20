function generateModelInputs() {
  // if the model selected is "Net Benefits" then the user will be prompted to enter a budget instead of a priority
  if (document.querySelector('input[name="model"]:checked').value === 'Net Benefits') {
      const container = document.getElementById('model-details');
      container.innerHTML = ''; // Clear previous inputs
      container.innerHTML = `<h3>Net Benefits Model Inputs</h3>`;
      container.innerHTML += `
        <label for="budget">Enter Budget ($):</label><br />
        <input type="number" id="budget" placeholder="e.g. 50000" /><br /><br />
      `;
      container.innerHTML += `
        <label for="priority">Select Priority:</label><span class="info-bubble" title="Select which value you would like PATH to prioritize.">?</span><br />
        <label><input type="radio" name="priority" value="Water Quality" /> Water Quality</label><br />
        <label><input type="radio" name="priority" value="Soil Erosion Prevention" /> Soil Erosion Prevention</label><br /><br />
      `;  
      container.innerHTML += `
        <label for="Value">Enter Economic Valuation:</label><br />
        <input type="number" id="Value" placeholder="Sddc Value" /><span class="info-bubble" title="Enter the dollar value of a 1 ton change in Sediment Discharge (SDDC). This is the biophysical indicator used for Water Quality. For a regional valuation table click HERE.">?</span><br />
        <input type="number" id="Value" placeholder="Sdyd Value" /><span class="info-bubble" title="Enter the dollar value of a 1 ton change in Sediment Yield (SDYD). This is the biophysical indicator used for Soil Erosion Prevention. For a regional valuation table click HERE.">?</span><br /><br />
      `;
      container.innerHTML += `
        <label for="treatment">Select Treatments:</label><br />
        <label><input type="checkbox" name="treatment" value="Mulch" /> Mulch</label><br /><br />
      `;
      container.innerHTML += `
        <button type="button" onclick="generateInputs()">Configure Selected Treatments</button>
      `;
      container.innerHTML += `
        <div id="treatment-details" style="margin-top: 30px;"></div>
      `;
      return;
    }
  // if the model selected is "Cost Effectiveness" then the user will be prompted to enter a treatment priority and threshold

      const model = document.querySelector('input[name="model"]:checked').value;
      const container = document.getElementById('model-details');
      container.innerHTML = ''; // Clear previous inputs
      container.innerHTML = `<h3>${model} Model Inputs</h3>`;
      container.innerHTML += `
        <label>Sediment Discharge Threshold (tons):</label><span class="info-bubble" title="Enter the level of total sediment discharge you wish to remain below. If left blank PATH will set no threshold for the given biophysical measure.">?</span></label><br/> <input type="number" id="Sddc Threshold" placeholder="1000" <br /><br /><br />
        <label>Sediment Yield Threshold (tons): </label><span class="info-bubble" title="Enter the level of sediment yield per-hillslope you wish each to remain below. If left blank PATH will set no threshold for the given biophysical measure.">?</span></label><br/><input type="number" id="Sdyd Threshold" placeholder="100" <br /><br /><br />
      `;  
       

      container.innerHTML += `
        <label for="treatment">Select Treatments:</label><br />
        <label><input type="checkbox" name="treatment" value="Mulch" /> Mulch</label><br /><br />
      `;  
      container.innerHTML += `
        <button type="button" onclick="generateInputs()">Configure Selected Treatments</button>
      `;
      container.innerHTML += `
        <div id="treatment-details" style="margin-top: 30px;"></div>
      `;
    }


  function generateInputs() {
      const checked = Array.from(document.querySelectorAll('input[name="treatment"]:checked')).map(el => el.value);
      const container = document.getElementById('treatment-details');
      container.innerHTML = ''; // Clear previous inputs
    
      if (checked.length === 0) {
        container.innerHTML = '<p>Please select at least one treatment.</p>';
        return;
      }
    
      checked.forEach(treatment => { 
        const id = treatment.replace(/\s+/g, '-');
        
        
      

        const div = document.createElement('div');
        div.className = 'treatment-box';
        div.innerHTML = `
          <h3>${treatment}</h3>
          <label for="qty-${id}">Quantity (select all that apply):</label><br />
          <label><input type="checkbox" name="qty-${id}" value="0.5"/>0.5 ton/acre</label><br />
          <label><input type="checkbox" name="qty-${id}" value="1"/>1 ton/acre</label><br />
          <label><input type="checkbox" name="qty-${id}" value="2"/>2 ton/acre</label><br /><br />
          
    
          <label for="cost-${id}">Treatment Cost:</label><br />
          <input type="number" id="cost-${id}" placeholder="$/ton" /><br /><br />

          <label for="fixed-${id}">Fixed Cost:</label><span class="info-bubble" title="Fixed cost refers to any cost incurred if this treatment is used regardless of quantity or acerage (e.g cost of hiring a helicopter for aerial application)">?</span><br />
          <input type="number" id="fixed-${id}" placeholder="$/treatment" /><br /><br />

          <label for ="slope">Slope Filter:</label><span class="info-bubble" title="PATH will only consider hillslopes greater than the specified Lower bound slope angle (in degrees) and less than the specified Upper bound slope angle (in degrees).">?</span><br />
          <input type="number" id="slope-${id}" placeholder="Lower bound"/> <input type="number" id="slope-${id}" placeholder="Upper bound"/> <br /><br />

          <label for="severity-${id}">Burn Severity Filter:</label><span class="info-bubble" title="PATH will only consider hillslopes with the selected burn severities.">?</span><br />
          <label><input type="checkbox" name="severity-${id}" value="1"/>Low</label><br />
          <label><input type="checkbox" name="severity-${id}" value="2"/>Moderate</label><br />
          <label><input type="checkbox" name="severity-${id}" value="3"/>High</label><br /><br />
        `;
    
        container.appendChild(div);
      });
    
      // ✅ Add the "Run PATH" button
      const runBtn = document.createElement('button');
      runBtn.textContent = 'Run PATH';
      runBtn.type = 'button';
      runBtn.onclick = runPATH;
      runBtn.style.marginTop = '20px';
      runBtn.style.display = 'block';
    
      container.appendChild(runBtn);
    }
    
    function runPATH() {
      const checked = Array.from(document.querySelectorAll('input[name="treatment"]:checked')).map(el => el.value);
    
      checked.forEach(treatment => {
        const id = treatment.replace(/\s+/g, '-');
        const qty = document.getElementById(`qty-${id}`).value;
        const cost = document.getElementById(`cost-${id}`).value;
        const fixed = document.getElementById(`fixed-${id}`).value;
    
        console.log(`Treatment: ${treatment}`);
        console.log(`- Quantity: ${qty} ton/acre`);
        console.log(`- Cost per acre: $${cost}`);
        console.log(`- Fixed cost: $${fixed}`);
      });
    
      alert("PATH model run complete. See console for details.");
    }
  




