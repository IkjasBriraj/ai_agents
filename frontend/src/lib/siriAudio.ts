// Apple iOS 27 Siri AI — Ultra Liquid Glass Sound Synthesizer (Web Audio API)
// Deep watery, bubbly, fluid morphing sound matching iOS 27 Liquid Glass Siri
// Reference: https://youtu.be/OToD4eu4eFs

let audioCtx: AudioContext | null = null;

const getAudioContext = (): AudioContext => {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
};

/**
 * Plays the iOS 27 Siri AI Liquid Glass activation sound.
 * Ultra-fluid, deeply watery, bubbly morphing sound.
 */
export const playSiriActivationSound = () => {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    // ─── MASTER CHAIN ───
    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.6, now);
    masterGain.connect(ctx.destination);

    const comp = ctx.createDynamicsCompressor();
    comp.threshold.setValueAtTime(-24, now);
    comp.knee.setValueAtTime(30, now);
    comp.ratio.setValueAtTime(4, now);
    comp.attack.setValueAtTime(0.005, now);
    comp.release.setValueAtTime(0.2, now);
    comp.connect(masterGain);

    // ═══════════════════════════════════════════════
    //  1. DEEP LIQUID WHOOSH — Heavy filtered noise, slow watery sweep
    // ═══════════════════════════════════════════════
    const noiseLen = ctx.sampleRate * 1.8;
    const noiseBuf = ctx.createBuffer(2, noiseLen, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const data = noiseBuf.getChannelData(ch);
      for (let i = 0; i < noiseLen; i++) {
        // Brownian noise (warmer, more liquid than white noise)
        data[i] = i === 0
          ? (Math.random() * 2 - 1) * 0.1
          : data[i - 1] + (Math.random() * 2 - 1) * 0.06;
        // Clamp
        if (data[i] > 1) data[i] = 1;
        if (data[i] < -1) data[i] = -1;
      }
    }

    const noiseSrc = ctx.createBufferSource();
    noiseSrc.buffer = noiseBuf;

    // Slow sweeping bandpass — like water swirling
    const noiseBP = ctx.createBiquadFilter();
    noiseBP.type = 'bandpass';
    noiseBP.Q.setValueAtTime(1.8, now);
    noiseBP.frequency.setValueAtTime(150, now);
    noiseBP.frequency.exponentialRampToValueAtTime(900, now + 0.3);
    noiseBP.frequency.exponentialRampToValueAtTime(1400, now + 0.5);
    noiseBP.frequency.exponentialRampToValueAtTime(500, now + 0.9);
    noiseBP.frequency.exponentialRampToValueAtTime(200, now + 1.5);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.0001, now);
    noiseGain.gain.linearRampToValueAtTime(0.35, now + 0.08);
    noiseGain.gain.setValueAtTime(0.30, now + 0.2);
    noiseGain.gain.linearRampToValueAtTime(0.22, now + 0.5);
    noiseGain.gain.exponentialRampToValueAtTime(0.06, now + 1.0);
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.6);

    noiseSrc.connect(noiseBP);
    noiseBP.connect(noiseGain);
    noiseGain.connect(comp);
    noiseSrc.start(now);
    noiseSrc.stop(now + 1.8);

    // ═══════════════════════════════════════════════
    //  2. BUBBLE CLUSTER — Multiple resonant filter pings at different times
    //     Like bubbles rising through liquid glass
    // ═══════════════════════════════════════════════
    const bubbleTimes = [0.0, 0.06, 0.14, 0.25, 0.38, 0.55, 0.72];
    const bubbleFreqs = [1800, 2400, 1200, 3000, 1600, 2100, 2800];
    const bubbleQs    = [30,   22,   35,   18,   28,   25,   20];
    const bubbleVols  = [0.10, 0.07, 0.12, 0.06, 0.09, 0.07, 0.05];

    bubbleTimes.forEach((t, i) => {
      const bStart = now + t;
      const bLen = ctx.sampleRate * 0.1;
      const bBuf = ctx.createBuffer(1, bLen, ctx.sampleRate);
      const bData = bBuf.getChannelData(0);
      for (let j = 0; j < bLen; j++) {
        bData[j] = (Math.random() * 2 - 1);
      }

      const bSrc = ctx.createBufferSource();
      bSrc.buffer = bBuf;

      const bFilter = ctx.createBiquadFilter();
      bFilter.type = 'bandpass';
      bFilter.Q.setValueAtTime(bubbleQs[i], bStart);
      bFilter.frequency.setValueAtTime(bubbleFreqs[i], bStart);
      bFilter.frequency.exponentialRampToValueAtTime(bubbleFreqs[i] * 0.4, bStart + 0.09);

      const bGain = ctx.createGain();
      bGain.gain.setValueAtTime(0.0001, bStart);
      bGain.gain.linearRampToValueAtTime(bubbleVols[i], bStart + 0.004);
      bGain.gain.exponentialRampToValueAtTime(0.0001, bStart + 0.09);

      bSrc.connect(bFilter);
      bFilter.connect(bGain);
      bGain.connect(comp);
      bSrc.start(bStart);
      bSrc.stop(bStart + 0.1);
    });

    // ═══════════════════════════════════════════════
    //  3. DEEP UNDERWATER MORPHING TONES — Very slow gliding, heavy vibrato
    // ═══════════════════════════════════════════════

    // LFO for vibrato/wobble effect on all tones
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.type = 'sine';
    lfo.frequency.setValueAtTime(3.5, now); // slow wobble
    lfoGain.gain.setValueAtTime(12, now);   // ±12Hz frequency modulation
    lfo.connect(lfoGain);
    lfo.start(now);
    lfo.stop(now + 1.8);

    // Tone A: Deep liquid bass drone — very slow glide
    const oscA = ctx.createOscillator();
    const gainA = ctx.createGain();
    oscA.type = 'sine';
    oscA.frequency.setValueAtTime(180, now);
    oscA.frequency.exponentialRampToValueAtTime(260, now + 0.4);
    oscA.frequency.exponentialRampToValueAtTime(220, now + 0.8);
    oscA.frequency.exponentialRampToValueAtTime(170, now + 1.3);
    lfoGain.connect(oscA.frequency); // Add wobble

    gainA.gain.setValueAtTime(0.0001, now);
    gainA.gain.linearRampToValueAtTime(0.18, now + 0.15);
    gainA.gain.setValueAtTime(0.16, now + 0.5);
    gainA.gain.exponentialRampToValueAtTime(0.04, now + 1.0);
    gainA.gain.exponentialRampToValueAtTime(0.0001, now + 1.5);

    oscA.connect(gainA);
    gainA.connect(comp);
    oscA.start(now);
    oscA.stop(now + 1.6);

    // Tone B: Mid liquid shimmer — glassy, resonant
    const oscB = ctx.createOscillator();
    const gainB = ctx.createGain();
    oscB.type = 'sine';
    oscB.frequency.setValueAtTime(420, now + 0.05);
    oscB.frequency.exponentialRampToValueAtTime(560, now + 0.4);
    oscB.frequency.exponentialRampToValueAtTime(480, now + 0.8);
    oscB.frequency.exponentialRampToValueAtTime(380, now + 1.2);
    lfoGain.connect(oscB.frequency);

    gainB.gain.setValueAtTime(0.0001, now + 0.05);
    gainB.gain.linearRampToValueAtTime(0.12, now + 0.2);
    gainB.gain.setValueAtTime(0.10, now + 0.5);
    gainB.gain.exponentialRampToValueAtTime(0.025, now + 0.9);
    gainB.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);

    oscB.connect(gainB);
    gainB.connect(comp);
    oscB.start(now + 0.05);
    oscB.stop(now + 1.5);

    // Tone C: High ethereal liquid glass ring
    const oscC = ctx.createOscillator();
    const gainC = ctx.createGain();
    oscC.type = 'sine';
    oscC.frequency.setValueAtTime(680, now + 0.1);
    oscC.frequency.exponentialRampToValueAtTime(880, now + 0.45);
    oscC.frequency.exponentialRampToValueAtTime(750, now + 0.85);
    oscC.frequency.exponentialRampToValueAtTime(620, now + 1.2);

    gainC.gain.setValueAtTime(0.0001, now + 0.1);
    gainC.gain.linearRampToValueAtTime(0.07, now + 0.25);
    gainC.gain.setValueAtTime(0.06, now + 0.5);
    gainC.gain.exponentialRampToValueAtTime(0.015, now + 0.9);
    gainC.gain.exponentialRampToValueAtTime(0.0001, now + 1.3);

    oscC.connect(gainC);
    gainC.connect(comp);
    oscC.start(now + 0.1);
    oscC.stop(now + 1.4);

    // ═══════════════════════════════════════════════
    //  4. SUB-BASS LIQUID THROB — Deep rumble like liquid glass vibrating
    // ═══════════════════════════════════════════════
    const subOsc = ctx.createOscillator();
    const subGain = ctx.createGain();
    subOsc.type = 'sine';
    subOsc.frequency.setValueAtTime(55, now);
    subOsc.frequency.exponentialRampToValueAtTime(85, now + 0.2);
    subOsc.frequency.exponentialRampToValueAtTime(45, now + 0.6);

    subGain.gain.setValueAtTime(0.0001, now);
    subGain.gain.linearRampToValueAtTime(0.25, now + 0.04);
    subGain.gain.setValueAtTime(0.20, now + 0.15);
    subGain.gain.exponentialRampToValueAtTime(0.05, now + 0.4);
    subGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.7);

    subOsc.connect(subGain);
    subGain.connect(comp);
    subOsc.start(now);
    subOsc.stop(now + 0.75);

    // ═══════════════════════════════════════════════
    //  5. SECONDARY LIQUID WHOOSH (tail) — Lighter, fading out
    // ═══════════════════════════════════════════════
    const tail = ctx.createBufferSource();
    tail.buffer = noiseBuf;

    const tailBP = ctx.createBiquadFilter();
    tailBP.type = 'bandpass';
    tailBP.Q.setValueAtTime(3, now + 0.4);
    tailBP.frequency.setValueAtTime(800, now + 0.4);
    tailBP.frequency.exponentialRampToValueAtTime(2000, now + 0.7);
    tailBP.frequency.exponentialRampToValueAtTime(400, now + 1.4);

    const tailGain = ctx.createGain();
    tailGain.gain.setValueAtTime(0.0001, now + 0.4);
    tailGain.gain.linearRampToValueAtTime(0.12, now + 0.55);
    tailGain.gain.exponentialRampToValueAtTime(0.03, now + 1.0);
    tailGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.5);

    tail.connect(tailBP);
    tailBP.connect(tailGain);
    tailGain.connect(comp);
    tail.start(now + 0.4);
    tail.stop(now + 1.6);

  } catch (err) {
    console.warn('[SiriAudio] Web Audio context skipped:', err);
  }
};

/**
 * Liquid glass processing pulse — bubbly, watery ping.
 */
export const playAgentProcessingPulse = () => {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;

    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.28, now);
    masterGain.connect(ctx.destination);

    // LPF for warmth
    const lpf = ctx.createBiquadFilter();
    lpf.type = 'lowpass';
    lpf.frequency.setValueAtTime(2400, now);
    lpf.connect(masterGain);

    // Rising bubble tone
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(220, now);
    osc.frequency.exponentialRampToValueAtTime(480, now + 0.12);
    osc.frequency.exponentialRampToValueAtTime(380, now + 0.3);

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.14, now + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.03, now + 0.2);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);

    osc.connect(gain);
    gain.connect(lpf);
    osc.start(now);
    osc.stop(now + 0.5);

    // Bubble pop noise burst
    const bLen = ctx.sampleRate * 0.06;
    const bBuf = ctx.createBuffer(1, bLen, ctx.sampleRate);
    const bData = bBuf.getChannelData(0);
    for (let i = 0; i < bLen; i++) {
      bData[i] = (Math.random() * 2 - 1);
    }

    const bSrc = ctx.createBufferSource();
    bSrc.buffer = bBuf;

    const bpf = ctx.createBiquadFilter();
    bpf.type = 'bandpass';
    bpf.Q.setValueAtTime(20, now);
    bpf.frequency.setValueAtTime(2000, now);
    bpf.frequency.exponentialRampToValueAtTime(900, now + 0.05);

    const bGain = ctx.createGain();
    bGain.gain.setValueAtTime(0.0001, now);
    bGain.gain.linearRampToValueAtTime(0.08, now + 0.003);
    bGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.05);

    bSrc.connect(bpf);
    bpf.connect(bGain);
    bGain.connect(lpf);
    bSrc.start(now);
    bSrc.stop(now + 0.06);

  } catch (err) {
    console.warn('[SiriAudio] Processing sound skipped:', err);
  }
};
