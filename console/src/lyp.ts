// Parses IHP SG13G2 KLayout .lyp XML (fetched from https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/e73adb4045731ddec21634146d536380057f6a26/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.lyp at commit e73adb4045731ddec21634146d536380057f6a26) into layer palette entries.
export interface LayerEntry {
  id: string;
  name: string;
  source: string;
  fillColor: string;
  frameColor: string;
  dither: string;
  visible: boolean;
}

function tagText(block: string, tag: string): string {
  const m = new RegExp(`<${tag}>([^<]*)</${tag}>`).exec(block);
  return m ? m[1].trim() : "";
}

export function parseLyp(xml: string): LayerEntry[] {
  const layers: LayerEntry[] = [];
  const pattern = /<properties>([\s\S]*?)<\/properties>/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(xml)) !== null) {
    const body = match[1];
    const name = tagText(body, "name");
    const source = tagText(body, "source");
    if (!name && !source) continue;
    layers.push({
      id: `${source || name}-${layers.length}`,
      name: name || source,
      source,
      fillColor: tagText(body, "fill-color") || "#888888",
      frameColor: tagText(body, "frame-color") || "#cccccc",
      dither: tagText(body, "dither-pattern") || "I0",
      visible: tagText(body, "visible") !== "false",
    });
  }
  return layers;
}
