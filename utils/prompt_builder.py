import re

LIGHTING_MAP = {
    "natural": "natural daylight",
    "golden": "golden hour backlight, warm sunset glow",
    "studio": "soft studio key light, professional lighting",
    "dramatic": "dramatic rim lighting, high contrast chiaroscuro",
    "neon": "soft neon glow, cyberpunk ambient light",
}

ANGLE_MAP = {
    "portrait": "eye-level portrait shot",
    "wide": "wide environmental landscape shot",
    "macro": "detailed macro close-up photography",
    "aerial": "aerial drone shot, bird's eye view",
}

LENS_MAP = {
    "lens85": "shot on 85mm portrait lens, f/1.4 aperture, shallow depth of field",
    "lens35": "shot on 35mm candid lens, f/2.0 aperture, street photography style",
    "lens24": "shot on 24mm wide angle lens, dramatic perspective",
    "canon": "captured on Canon EOS R5 DSLR, sharp focus, high-end photography",
}


def parse_midjourney_flags(prompt: str) -> tuple[str, dict[str, any]]:
    """
    Parses Midjourney-style flags from a prompt string.
    Supported flags:
      --ar <ratio> (e.g. 16:9, 1:1, 9:16)
      --no <negative prompt text>
      --seed <number>
    
    Returns:
      (cleaned_prompt, overrides_dict)
    """
    overrides = {}

    # 1. Parse --ar
    ar_match = re.search(r'--ar\s+([0-9]+[:x/][0-9]+|[0-9]+)', prompt, re.IGNORECASE)
    if ar_match:
        ratio = ar_match.group(1).replace('x', ':').replace('/', ':')
        overrides['aspect_ratio'] = ratio
        prompt = prompt.replace(ar_match.group(0), '')

    # 2. Parse --seed
    seed_match = re.search(r'--seed\s+(\d+)', prompt, re.IGNORECASE)
    if seed_match:
        try:
            overrides['seed'] = int(seed_match.group(1))
        except ValueError:
            pass
        prompt = prompt.replace(seed_match.group(0), '')

    # 3. Parse --no
    # Capture everything after --no until either another flag starting with ' --' or end of string.
    no_match = re.search(r'--no\s+((?:(?! --).)*)', prompt, re.IGNORECASE)
    if no_match:
        overrides['negative_prompt'] = no_match.group(1).strip()
        prompt = prompt.replace(no_match.group(0), '')

    # Clean up whitespace
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    return prompt, overrides


def build_prompt(subject: str, lighting: str | None, angle: str | None, lens: str | None) -> str:
    """
    Builds a detailed prompt by appending chosen photography components.
    """
    parts = [subject.strip()]
    if lighting and lighting in LIGHTING_MAP:
        parts.append(LIGHTING_MAP[lighting])
    if angle and angle in ANGLE_MAP:
        parts.append(ANGLE_MAP[angle])
    if lens and lens in LENS_MAP:
        parts.append(LENS_MAP[lens])
    return ", ".join([p for p in parts if p])
