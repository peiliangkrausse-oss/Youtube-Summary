export function guideHtml() {
  return `
      <div class="setup-guide">
        <div class="hero">
        <h2>Run your youtube summaries locally on device</h2>
        <p>This app summarizes with AI running on your computer. No cloud. Never run out of tokens. Infinite usage.</p>
        <p>WatchLess works with LM Studio or Ollama. Both are free tools that run AI directly on your computer, so your summaries stay local.</p>
      </div>

      <div class="guide-flow">
        <section class="guide-step">
          <div class="step-kicker">Step 1</div>
          <h3>Choose your local AI app</h3>
          <p>You can use <a href="https://lmstudio.ai/download" target="_blank" rel="noopener">LM Studio</a> or <a href="https://ollama.com/download" target="_blank" rel="noopener">Ollama</a>. In WatchLess, pick the same provider in the model section before you test the connection.</p>
        </section>

        <section class="guide-step guide-step-with-media guide-step-compact-media">
          <div>
            <div class="step-kicker">Step 2</div>
            <h3>Find a model</h3>
            <p>In LM Studio, open the left sidebar and click <strong>Model Search</strong>. In Ollama, you will download models with a simple Terminal command such as <strong>ollama pull gemma4:latest</strong>.</p>
          </div>
          <figure class="guide-figure-compact">
            <img src="/static/images/guide/lm-studio-model-search.png" alt="LM Studio sidebar with the Model Search button highlighted">
          </figure>
        </section>

        <section class="guide-step guide-step-with-media">
          <div>
            <div class="step-kicker">Step 3</div>
            <h3>Download a model that fits your RAM</h3>
            <p>Choose a model that suits your computer memory. Smaller models are faster and safer for laptops; larger models need more memory.</p>
            <div class="ram-list">
              <h4>Recommended models by RAM</h4>
              <ul>
                <li><strong>16 GB RAM and below:</strong> Gemma E4B or Gemma 4 12B.</li>
                <li><strong>24 GB+ RAM:</strong> ChatGPT OSS 20B or Gemma 4 12B.</li>
                <li><strong>32 GB+ RAM:</strong> Gemma 4, Qwen 3.6, or 26B-27B class models.</li>
              </ul>
            </div>
          </div>
          <figure class="guide-figure-wide">
            <img src="/static/images/guide/lm-studio-gpt-oss-model.png" alt="LM Studio model detail screen showing GPT-OSS 20B download options">
          </figure>
        </section>

        <section class="guide-step guide-step-with-media">
          <div>
            <div class="step-kicker">Step 4</div>
            <h3>Start the local server</h3>
            <p>For LM Studio, open <strong>Developer</strong> and switch the local server to <strong>Status: Running</strong>. For Ollama, open the Ollama app or run <strong>ollama serve</strong> if it is not already running.</p>
            <p>LM Studio usually uses port <strong>1234</strong>. Ollama usually uses <strong>11434</strong>. WatchLess checks the correct address for the provider you selected.</p>
          </div>
          <figure>
            <img src="/static/images/guide/lm-studio-local-server.png" alt="LM Studio Developer screen showing the Local Server running on port 1234">
          </figure>
        </section>

        <section class="guide-step">
          <div class="step-kicker">Step 5</div>
          <h3>Select the model in WatchLess</h3>
          <p>Once connected, WatchLess will show your available models. If you use LM Studio, load one model before summarizing. If you use Ollama, simply choose any installed model from the list.</p>
        </section>
      </div>
    </div>`;
}
