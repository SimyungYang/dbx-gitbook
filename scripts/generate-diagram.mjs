import { JSDOM } from 'jsdom';
import rough from 'roughjs';
import fs from 'fs';

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
const document = dom.window.document;

function createSvg(width, height) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  // 배경
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bg.setAttribute('width', width);
  bg.setAttribute('height', height);
  bg.setAttribute('fill', '#ffffff');
  svg.appendChild(bg);

  return svg;
}

function addText(svg, x, y, text, { fontSize = 16, fontWeight = 'bold', fill = '#1e1e1e', anchor = 'middle' } = {}) {
  const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  t.setAttribute('x', x);
  t.setAttribute('y', y);
  t.setAttribute('text-anchor', anchor);
  t.setAttribute('dominant-baseline', 'middle');
  t.setAttribute('font-family', "'Segoe UI', system-ui, -apple-system, sans-serif");
  t.setAttribute('font-size', fontSize);
  t.setAttribute('font-weight', fontWeight);
  t.setAttribute('fill', fill);
  t.textContent = text;
  svg.appendChild(t);
}

function addMultilineText(svg, x, y, lines, options = {}) {
  const { fontSize = 14, lineHeight = 20, ...rest } = options;
  lines.forEach((line, i) => {
    addText(svg, x, y + i * lineHeight, line, { fontSize, ...rest });
  });
}

// =============================================
// RAG 체인 아키텍처 다이어그램
// =============================================
function generateRagChain() {
  const width = 750;
  const height = 220;
  const svg = createSvg(width, height);
  const rc = rough.svg(svg);

  const colors = {
    blue: { fill: '#dbeafe', stroke: '#3b82f6' },
    green: { fill: '#dcfce7', stroke: '#22c55e' },
    purple: { fill: '#f3e8ff', stroke: '#a855f7' },
    gray: { fill: '#f1f5f9', stroke: '#64748b' },
  };

  // 사용자 질문 박스
  const q = rc.rectangle(20, 70, 120, 60, {
    fill: colors.gray.fill, stroke: colors.gray.stroke,
    fillStyle: 'solid', roughness: 1.2, strokeWidth: 1.5,
  });
  svg.appendChild(q);
  addText(svg, 80, 95, '사용자 질문', { fontSize: 14 });
  addText(svg, 80, 112, '💬', { fontSize: 16, fontWeight: 'normal' });

  // Retriever 박스
  const r = rc.rectangle(190, 40, 160, 120, {
    fill: colors.blue.fill, stroke: colors.blue.stroke,
    fillStyle: 'solid', roughness: 1.2, strokeWidth: 1.5,
  });
  svg.appendChild(r);
  addText(svg, 270, 68, 'Retriever', { fontSize: 16 });
  addText(svg, 270, 88, '검색기', { fontSize: 12, fontWeight: 'normal', fill: '#64748b' });
  addMultilineText(svg, 270, 115, ['Vector Search에서', '관련 청크 검색'], {
    fontSize: 12, fontWeight: 'normal', fill: '#475569', lineHeight: 16,
  });

  // Augmenter 박스
  const a = rc.rectangle(400, 40, 160, 120, {
    fill: colors.green.fill, stroke: colors.green.stroke,
    fillStyle: 'solid', roughness: 1.2, strokeWidth: 1.5,
  });
  svg.appendChild(a);
  addText(svg, 480, 68, 'Augmenter', { fontSize: 16 });
  addText(svg, 480, 88, '증강기', { fontSize: 12, fontWeight: 'normal', fill: '#64748b' });
  addMultilineText(svg, 480, 115, ['프롬프트에', '검색 결과를 주입'], {
    fontSize: 12, fontWeight: 'normal', fill: '#475569', lineHeight: 16,
  });

  // Generator 박스
  const g = rc.rectangle(610, 40, 120, 120, {
    fill: colors.purple.fill, stroke: colors.purple.stroke,
    fillStyle: 'solid', roughness: 1.2, strokeWidth: 1.5,
  });
  svg.appendChild(g);
  addText(svg, 670, 68, 'Generator', { fontSize: 16 });
  addText(svg, 670, 88, '생성기', { fontSize: 12, fontWeight: 'normal', fill: '#64748b' });
  addMultilineText(svg, 670, 115, ['LLM이', '답변 생성'], {
    fontSize: 12, fontWeight: 'normal', fill: '#475569', lineHeight: 16,
  });

  // 화살표
  const arrow1 = rc.line(140, 100, 190, 100, { stroke: '#64748b', strokeWidth: 1.5, roughness: 0.8 });
  svg.appendChild(arrow1);
  const arrow2 = rc.line(350, 100, 400, 100, { stroke: '#64748b', strokeWidth: 1.5, roughness: 0.8 });
  svg.appendChild(arrow2);
  const arrow3 = rc.line(560, 100, 610, 100, { stroke: '#64748b', strokeWidth: 1.5, roughness: 0.8 });
  svg.appendChild(arrow3);

  // 화살표 머리 (SVG triangle)
  for (const tipX of [190, 400, 610]) {
    const arrowHead = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    arrowHead.setAttribute('points', `${tipX},100 ${tipX - 8},95 ${tipX - 8},105`);
    arrowHead.setAttribute('fill', '#64748b');
    svg.appendChild(arrowHead);
  }

  // 품질 영향도 라벨
  addText(svg, 270, 180, '60%', { fontSize: 13, fill: colors.blue.stroke, fontWeight: 'bold' });
  addText(svg, 480, 180, '25%', { fontSize: 13, fill: colors.green.stroke, fontWeight: 'bold' });
  addText(svg, 670, 180, '15%', { fontSize: 13, fill: colors.purple.stroke, fontWeight: 'bold' });
  addText(svg, 375, 205, '← 품질 영향도', { fontSize: 11, fill: '#94a3b8', fontWeight: 'normal' });

  return svg.outerHTML;
}

// SVG 생성 및 저장
const outputDir = '/Users/simyung.yang/Dev/03-dbx-gitbook/docs-mintlify/images/diagrams';

const ragSvg = generateRagChain();
fs.writeFileSync(`${outputDir}/rag-chain.svg`, ragSvg);
console.log('✅ rag-chain.svg generated');
