import { Stage, Layer, Text, Rect, Line, Group } from 'react-konva';
import { useMemo } from 'react';

/**
 * React-Konva based virtual whiteboard.
 *
 * Renders board elements emitted by the Gemini orchestrator.
 * Each element has: { id, type, content, position, style }
 *
 * Types:
 *   text     — regular text
 *   heading  — large bold heading
 *   example  — highlighted box with text
 *   formula  — math formula rendered as text (KaTeX not available in canvas)
 *   diagram  — simple labelled box diagram
 *
 * @param {{ elements: Array, width: number, height: number }} props
 */
export default function VirtualBoard({ elements = [], width = 800, height = 500 }) {
  const rendered = useMemo(() => {
    return elements.map((el, idx) => {
      const x = el.position?.x ?? 20;
      const y = el.position?.y ?? 20 + idx * 60;
      const color = el.style?.color || '#f1f5f9';
      const fontSize = el.style?.fontSize || 18;
      const key = el.id || `el-${idx}`;

      switch (el.type) {
        case 'heading':
          return (
            <Text
              key={key}
              x={x}
              y={y}
              text={el.content}
              fontSize={fontSize || 28}
              fontStyle="bold"
              fill={color || '#60a5fa'}
              width={width - x - 20}
              wrap="word"
            />
          );

        case 'example':
          return (
            <Group key={key} x={x} y={y}>
              <Rect
                width={width - x - 20}
                height={Math.max(60, (el.content?.length || 0) * 0.4 + 40)}
                fill="#1e3a5f"
                cornerRadius={6}
                stroke="#3b82f6"
                strokeWidth={1}
              />
              <Text
                x={12}
                y={12}
                text={el.content}
                fontSize={fontSize}
                fill={color}
                width={width - x - 44}
                wrap="word"
              />
            </Group>
          );

        case 'formula':
          return (
            <Group key={key} x={x} y={y}>
              <Rect
                width={width - x - 20}
                height={50}
                fill="#1a1a2e"
                cornerRadius={4}
                stroke="#8b5cf6"
                strokeWidth={1}
              />
              <Text
                x={12}
                y={14}
                text={el.content}
                fontSize={fontSize || 20}
                fontFamily="monospace"
                fill="#c4b5fd"
                width={width - x - 44}
                wrap="word"
              />
            </Group>
          );

        case 'diagram': {
          const boxW = 160;
          const boxH = 50;
          const labels = Array.isArray(el.content)
            ? el.content
            : [el.content];
          return (
            <Group key={key} x={x} y={y}>
              {labels.map((label, li) => (
                <Group key={li} x={li * (boxW + 40)} y={0}>
                  <Rect
                    width={boxW}
                    height={boxH}
                    fill="#1e293b"
                    stroke="#475569"
                    strokeWidth={1}
                    cornerRadius={4}
                  />
                  <Text
                    x={8}
                    y={14}
                    text={String(label)}
                    fontSize={14}
                    fill="#94a3b8"
                    width={boxW - 16}
                    align="center"
                  />
                  {li < labels.length - 1 && (
                    <Line
                      points={[boxW, boxH / 2, boxW + 40, boxH / 2]}
                      stroke="#475569"
                      strokeWidth={2}
                    />
                  )}
                </Group>
              ))}
            </Group>
          );
        }

        default:
          // 'text' and anything else
          return (
            <Text
              key={key}
              x={x}
              y={y}
              text={el.content}
              fontSize={fontSize}
              fill={color}
              width={width - x - 20}
              wrap="word"
            />
          );
      }
    });
  }, [elements, width, height]);

  return (
    <Stage
      width={width}
      height={height}
      style={{ background: '#0d1117', borderRadius: '0.5rem' }}
    >
      <Layer>
        {/* Background */}
        <Rect x={0} y={0} width={width} height={height} fill="#0d1117" />
        {rendered}
      </Layer>
    </Stage>
  );
}
