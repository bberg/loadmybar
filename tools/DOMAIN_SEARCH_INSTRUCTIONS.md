# Domain Search Instructions for Sub-Agents

## Overview
Find available domain names for Audio Tools Network sites using the Domainr API.

## Tool Location
```
/Users/bb/www/audio-tools-network/shared/tools/domain_search_api.py
```

## Usage
```bash
cd /Users/bb/www/audio-tools-network/shared/tools
python3 domain_search_api.py "search query" "extra,domains,to,check"
```

## Process

### Step 1: Run the Domain Search
Use the API tool with:
- First arg: Main search query (e.g., "tone generator")
- Second arg: Comma-separated list of extra domains to check

Example:
```bash
python3 domain_search_api.py "binaural beats" "binauralbeats.co,brainbeats.com,focusbeats.io"
```

### Step 2: Review Results
The tool outputs:
- ✅ AVAILABLE - Domain can be registered
- ❌ active/taken - Domain is registered

### Step 3: Rank Available Domains
Rank by these criteria:
1. **Exact match** - e.g., "tonegenerator.com" for tone generator
2. **SEO value** - Contains keywords people search for
3. **TLD preference** - .com > .co > .io > .org > others
4. **Length** - Shorter is better (under 15 chars ideal)
5. **Brandability** - Memorable, easy to spell

---

## Sites to Search

### 1. ToneGenerator (port 8002)
**Topic**: Online tone generator, frequency generator, waveform generator for audio testing, music, hearing tests
**Seed ideas**: tonegen, puretone, waveformgen, audiofreq, tonemaker, freqgen

### 2. BinauralBeats (port 8003)
**Topic**: Binaural beats generator for meditation, focus, sleep, brainwave entrainment
**Seed ideas**: binauralgen, brainbeats, binauralsound, focusbeats, thetawaves

### 3. DroneGenerator (port 8004)
**Topic**: Ambient drone generator for meditation, yoga, sound healing, relaxation
**Seed ideas**: dronegen, ambientdrone, sounddrone, meditationdrone, dronescapes

### 4. FrequencyGenerator (port 8005)
**Topic**: Precision frequency generator for speaker testing, calibration, hearing tests
**Seed ideas**: freqgen, audiotest, speakertest, freqmaker, calibrationtone

### 5. Metronome (port 8006)
**Topic**: Online metronome for musicians, tempo practice, rhythm training
**Seed ideas**: metronomeonline, tempotool, beatkeeper, rhythmtool, clicktrack

---

## Output Format

For each site, provide:

```markdown
## [Site Name] Domain Results

### Available Domains
| Domain | Verified | Notes |
|--------|----------|-------|
| example.com | ✅ WHOIS confirmed | Best option - short, brandable |
| example.io | ✅ WHOIS confirmed | Good alternative |

### Recommendation
**Primary**: example.com
**Backup**: example.io
**Reasoning**: [Why this domain is best]
```

---

## Notes
- DNS check is fast but not 100% accurate (parked domains may not resolve)
- Always verify top picks with WHOIS
- .io and .co WHOIS may not work - use registrar lookup for those
- Some good domains may be registered but for sale - note these separately
