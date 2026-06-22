# CAA Design System

> Guia visual e técnico para codificar a interface do **CAA — Corporate Actions Agent**, um produto fintech de auditoria com IA.  
> Use este documento como referência para agentes de código, designers e desenvolvedores manterem consistência visual em telas, componentes e interações.

---

## 1. Essência visual

O CAA deve transmitir:

- **Confiança institucional**
- **Precisão de auditoria**
- **Clareza documental**
- **IA explicável, sem estética sci-fi**
- **Fintech moderna, calma e editorial**
- **Interface técnica, mas acessível**

A identidade parte da ideia de **documentos financeiros sendo analisados por IA**, com destaque para o motivo visual de **bounding boxes**, **corner brackets**, campos extraídos, evidências e status de validação.

Evite qualquer linguagem visual excessivamente futurista, neon, robótica, gamer ou bancária genérica.

---

## 2. Paleta oficial

Use poucas cores. O produto deve parecer sóbrio, limpo e auditável.

```css
:root {
  /* Brand */
  --caa-navy: #101C2C;
  --caa-paper: #F4EFE4;
  --caa-paper-soft: #FAF7F0;
  --caa-graphite: #4A4F58;

  /* Status */
  --caa-approved: #1E9E6B;
  --caa-review: #E0A23E;
  --caa-rejected: #C24B3D;

  /* Neutrals */
  --caa-border: rgba(16, 28, 44, 0.28);
  --caa-border-strong: rgba(16, 28, 44, 0.72);
  --caa-muted: rgba(74, 79, 88, 0.72);
  --caa-disabled-bg: #E3DED4;
  --caa-disabled-text: rgba(74, 79, 88, 0.58);

  /* Feedback backgrounds */
  --caa-approved-soft: rgba(30, 158, 107, 0.12);
  --caa-review-soft: rgba(224, 162, 62, 0.14);
  --caa-rejected-soft: rgba(194, 75, 61, 0.12);

  /* Effects */
  --caa-shadow-sm: 0 2px 6px rgba(16, 28, 44, 0.08);
  --caa-shadow-md: 0 8px 24px rgba(16, 28, 44, 0.10);
}
```

### Uso recomendado

| Cor | Uso |
|---|---|
| `#101C2C` | Texto principal, ícones, botões primários, bordas fortes |
| `#F4EFE4` | Fundo principal do produto |
| `#FAF7F0` | Cards e superfícies elevadas |
| `#4A4F58` | Texto secundário, placeholders, metadados |
| `#1E9E6B` | Aprovado, validado, confiança alta |
| `#E0A23E` | Revisão necessária, atenção |
| `#C24B3D` | Rejeitado, erro, inconsistência |

---

## 3. Princípios de design

### 3.1 Precisão antes de decoração

A interface deve parecer uma ferramenta de auditoria. Cada elemento visual precisa ter função clara.

### 3.2 Documento como metáfora central

Use linhas finas, caixas, marcações, campos destacados, tags de porcentagem e pequenos indicadores para reforçar o conceito de extração de dados e evidência documental.

### 3.3 Status sempre visível

Aprovação, revisão e rejeição devem ter cores consistentes em todo o produto.

### 3.4 Menos brilho, mais autoridade

Não usar glassmorphism, neon, glow, 3D, sombras pesadas ou gradientes decorativos.  
O único gradiente permitido é o **confidence meter**, indo de vermelho para âmbar e verde.

### 3.5 Legibilidade em primeiro lugar

Mesmo com estética técnica, a UI deve ser clara, espaçada e confortável.

---

## 4. Tipografia

### 4.1 Fonte principal

Use uma fonte grotesk/sans moderna, precisa e neutra.

Sugestões:

- `Inter`
- `IBM Plex Sans`
- `Satoshi`
- `Geist`
- `Helvetica Neue`

```css
--font-sans: "Inter", "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
```

### 4.2 Fonte técnica

Use monospace para dados financeiros, códigos, percentuais, datas, IDs e valores extraídos.

Sugestões:

- `IBM Plex Mono`
- `JetBrains Mono`
- `Geist Mono`
- `SFMono-Regular`

```css
--font-mono: "IBM Plex Mono", "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
```

### 4.3 Escala tipográfica

```css
--text-xs: 0.75rem;   /* 12px */
--text-sm: 0.875rem;  /* 14px */
--text-md: 1rem;      /* 16px */
--text-lg: 1.125rem;  /* 18px */
--text-xl: 1.5rem;    /* 24px */
--text-2xl: 2rem;     /* 32px */
--text-3xl: 3rem;     /* 48px */
```

### 4.4 Regras de texto

- Títulos: sans-serif, peso 600 ou 700.
- Labels: uppercase, tracking leve, 11–12px.
- Dados: monospace, peso 500.
- Corpo: sans-serif, 14–16px.
- Evite blocos longos sem hierarquia.

---

## 5. Espaçamento, radius e stroke

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 14px;
  --radius-xl: 22px;

  --stroke-ui: 2px;
}
```

### Regras

- Inputs, cards e botões: **8px de radius** por padrão.
- App icons e favicons: cantos mais arredondados, entre **18px e 28px**.
- Ícones: stroke de **2px**, linecap e linejoin arredondados.
- Bordas devem ser finas, nítidas e em navy com opacidade reduzida.

---

## 6. Layout

### 6.1 Fundo

O fundo padrão deve ser paper-toned:

```css
body {
  background: var(--caa-paper);
  color: var(--caa-navy);
  font-family: var(--font-sans);
}
```

### 6.2 Grid

Use grids limpos, com bastante whitespace.

```css
.caa-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 24px;
}
```

### 6.3 Superfícies

Cards e painéis devem parecer digitais, não fotográficos.

```css
.caa-surface {
  background: var(--caa-paper-soft);
  border: 1px solid var(--caa-border);
  border-radius: var(--radius-md);
  box-shadow: var(--caa-shadow-sm);
}
```

---

## 7. Motivo visual: corner brackets

O CAA deve usar pequenos **corner brackets** como assinatura visual. Eles representam:

- Detecção de documento
- Campo auditado
- Evidência capturada
- Bounding box de IA

### Exemplo CSS

```css
.caa-bracket-frame {
  position: relative;
}

.caa-bracket-frame::before,
.caa-bracket-frame::after {
  content: "";
  position: absolute;
  width: 18px;
  height: 18px;
  border-color: var(--caa-navy);
  border-style: solid;
  pointer-events: none;
}

.caa-bracket-frame::before {
  top: 12px;
  left: 12px;
  border-width: 2px 0 0 2px;
}

.caa-bracket-frame::after {
  right: 12px;
  bottom: 12px;
  border-width: 0 2px 2px 0;
}
```

### Uso correto

Use brackets em:

- Cards de evidência
- Dropzones de upload
- Campos extraídos de documentos
- Estados de foco
- Empty states relacionados a análise documental

Evite usar brackets em excesso em todos os componentes ao mesmo tempo.

---

## 8. Iconografia

### 8.1 Estilo

Todos os ícones devem ser:

- Outline
- Stroke `2px`
- Cor `#101C2C`
- Rounded linecap
- Rounded linejoin
- Sem preenchimento interno
- Sem texto dentro do ícone
- Viewbox recomendado: `24x24`

```tsx
<svg
  width="24"
  height="24"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  strokeWidth="2"
  strokeLinecap="round"
  strokeLinejoin="round"
/>
```

### 8.2 Ícones essenciais

O sistema deve conter ícones para:

- Documento
- Documento escaneado
- Olho / revisão visual
- Busca em texto
- Corner bracket / detecção
- Gauge de confiança
- Check em círculo
- X em círculo
- Flag de atenção
- Clock / histórico
- Banco de dados
- Chain link / relação
- Upload em bandeja
- Tag de porcentagem
- Balança / auditoria

### 8.3 Biblioteca recomendada

Pode usar `lucide-react` como base, desde que todos os ícones sejam customizados para manter:

```tsx
strokeWidth={2}
absoluteStrokeWidth
```

---

## 9. Botões

### 9.1 Botão primário

Uso: ação principal da tela.

```css
.caa-button-primary {
  height: 44px;
  padding: 0 20px;
  border: 1px solid var(--caa-navy);
  border-radius: var(--radius-md);
  background: var(--caa-navy);
  color: var(--caa-paper);
  font-weight: 600;
  box-shadow: var(--caa-shadow-sm);
}
```

### 9.2 Botão secundário

Uso: ação alternativa.

```css
.caa-button-secondary {
  height: 44px;
  padding: 0 20px;
  border: 1px solid var(--caa-border-strong);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--caa-navy);
  font-weight: 600;
}
```

### 9.3 Botões de status

```css
.caa-button-approved {
  background: var(--caa-approved);
  color: white;
}

.caa-button-review {
  background: var(--caa-review);
  color: white;
}

.caa-button-rejected {
  background: var(--caa-rejected);
  color: white;
}
```

### 9.4 Estados

- Hover: aumentar contraste levemente, sem glow.
- Focus: usar outline navy + bracket sutil quando fizer sentido.
- Disabled: fundo `#E3DED4`, texto graphite com baixa opacidade.
- Loading: manter largura fixa e trocar texto por spinner discreto.

---

## 10. Inputs

### 10.1 Campo de texto

```css
.caa-input {
  height: 42px;
  width: 100%;
  border: 1px solid var(--caa-border-strong);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--caa-navy);
  padding: 0 12px;
  font-size: var(--text-sm);
}

.caa-input::placeholder {
  color: var(--caa-muted);
}

.caa-input:focus {
  outline: 2px solid rgba(16, 28, 44, 0.16);
  border-color: var(--caa-navy);
}
```

### 10.2 Labels

```css
.caa-label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--caa-navy);
  font-weight: 700;
}
```

### 10.3 Select

O select deve seguir o mesmo visual do input, com chevron simples em navy.

### 10.4 Search bar

A busca deve conter ícone de lupa à esquerda, stroke navy 2px.

### 10.5 Upload dropzone

A dropzone deve usar borda tracejada e brackets.

```css
.caa-dropzone {
  position: relative;
  min-height: 128px;
  border: 1.5px dashed var(--caa-border-strong);
  border-radius: var(--radius-md);
  background: rgba(250, 247, 240, 0.64);
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--caa-navy);
}
```

---

## 11. Badges de status

### 11.1 Formato

Badges devem ser pequenos, pill-shaped, com ícone discreto.

```css
.caa-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
```

### 11.2 Variações

```css
.caa-badge-approved {
  background: var(--caa-approved);
  color: white;
}

.caa-badge-review {
  background: var(--caa-review);
  color: white;
}

.caa-badge-rejected {
  background: var(--caa-rejected);
  color: white;
}
```

### 11.3 Badges suaves

Use versões suaves dentro de cards ou tabelas densas.

```css
.caa-badge-approved-soft {
  background: var(--caa-approved-soft);
  color: var(--caa-approved);
}
```

---

## 12. Confidence meter

O medidor de confiança é o único componente que pode usar gradiente.

```css
.caa-confidence-meter {
  height: 14px;
  border-radius: 999px;
  border: 1px solid var(--caa-navy);
  background: linear-gradient(
    90deg,
    var(--caa-rejected) 0%,
    var(--caa-review) 50%,
    var(--caa-approved) 100%
  );
}
```

Use com escala `0%` à esquerda e `100%` à direita.  
Opcionalmente, exiba um marcador vertical indicando a confiança atual.

---

## 13. Evidence card

O Evidence Card é o componente mais importante da identidade do CAA.

Ele representa o vínculo entre:

- Campo extraído
- Valor identificado
- Confiança da IA
- Trecho de evidência
- Página de origem

### Estrutura recomendada

```tsx
type EvidenceCardProps = {
  field: string;
  value: string;
  confidence: number;
  evidence: string;
  page: number;
  status?: "approved" | "review" | "rejected";
};
```

### Visual

```css
.caa-evidence-card {
  position: relative;
  background: var(--caa-paper-soft);
  border: 1px solid var(--caa-border-strong);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--caa-shadow-sm);
}

.caa-evidence-row {
  display: grid;
  grid-template-columns: 96px 1fr auto;
  gap: 12px;
  align-items: center;
}

.caa-evidence-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--caa-navy);
}

.caa-evidence-value {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--caa-navy);
}

.caa-evidence-quote {
  margin-top: 16px;
  padding-left: 14px;
  border-left: 2px solid var(--caa-navy);
  color: var(--caa-graphite);
  font-size: 13px;
}
```

### Uso

```tsx
<EvidenceCard
  field="Payment Amount"
  value="USD 0.3750"
  confidence={97}
  evidence="...extracted field appears near payment amount..."
  page={12}
  status="approved"
/>
```

---

## 14. Cards e painéis

Cards devem ter aparência de folha técnica digital.

```css
.caa-card {
  background: var(--caa-paper-soft);
  border: 1px solid var(--caa-border);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--caa-shadow-sm);
}
```

### Cabeçalho de card

```css
.caa-card-title {
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--caa-navy);
}
```

---

## 15. Tabelas

Tabelas devem parecer relatórios de auditoria.

### Regras

- Header uppercase pequeno.
- Linhas com borda fina.
- Valores financeiros em monospace.
- Status sempre por badge.
- Hover discreto em paper-soft.
- Não usar zebra muito forte.

```css
.caa-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.caa-table th {
  text-align: left;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--caa-muted);
  padding: 12px;
  border-bottom: 1px solid var(--caa-border);
}

.caa-table td {
  padding: 14px 12px;
  border-bottom: 1px solid var(--caa-border);
  color: var(--caa-navy);
}
```

---

## 16. Estados da interface

### 16.1 Empty state

Use ícone outline + mensagem curta + ação clara.

Não usar ilustrações exageradas.

### 16.2 Loading

Use skeletons discretos em graphite com baixa opacidade.

```css
.caa-skeleton {
  background: rgba(74, 79, 88, 0.16);
  border-radius: 6px;
}
```

### 16.3 Error

Erro deve usar brick red, mas sem agressividade visual.

### 16.4 Success

Sucesso deve usar emerald, preferencialmente com check pequeno.

---

## 17. Favicon e app icon

O favicon principal do CAA deve ser:

- Fundo navy `#101C2C`
- Símbolo central off-white `#F4EFE4`
- Um `C` geométrico marcante
- Um `A` simplificado dentro ou associado ao `C`
- Pequeno ponto/status emerald `#1E9E6B`
- Brackets nos cantos como assinatura de auditoria documental

### Regras

- Não usar o texto completo “CAA” no favicon.
- Priorizar leitura em 16x16 e 32x32.
- Usar formas grossas e poucos detalhes.
- O ponto verde deve ser visível, mas não dominar.

---

## 18. Exemplo de tokens para Tailwind

```ts
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        caa: {
          navy: "#101C2C",
          paper: "#F4EFE4",
          paperSoft: "#FAF7F0",
          graphite: "#4A4F58",
          approved: "#1E9E6B",
          review: "#E0A23E",
          rejected: "#C24B3D",
        },
      },
      borderRadius: {
        caa: "8px",
      },
      boxShadow: {
        caaSm: "0 2px 6px rgba(16, 28, 44, 0.08)",
        caaMd: "0 8px 24px rgba(16, 28, 44, 0.10)",
      },
      fontFamily: {
        sans: ["Inter", "IBM Plex Sans", "Arial", "sans-serif"],
        mono: ["IBM Plex Mono", "JetBrains Mono", "monospace"],
      },
    },
  },
};
```

---

## 19. Exemplo de botão em React

```tsx
type ButtonVariant =
  | "primary"
  | "secondary"
  | "approved"
  | "review"
  | "rejected"
  | "disabled";

type ButtonProps = {
  variant?: ButtonVariant;
  children: React.ReactNode;
  disabled?: boolean;
};

export function CaaButton({
  variant = "primary",
  children,
  disabled,
}: ButtonProps) {
  const base =
    "inline-flex h-11 items-center justify-center rounded-[8px] px-5 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[#101C2C]/20";

  const variants = {
    primary:
      "border border-[#101C2C] bg-[#101C2C] text-[#F4EFE4] shadow-[0_2px_6px_rgba(16,28,44,0.08)] hover:bg-[#17263A]",
    secondary:
      "border border-[#101C2C]/70 bg-transparent text-[#101C2C] hover:bg-[#101C2C]/5",
    approved:
      "border border-[#1E9E6B] bg-[#1E9E6B] text-white hover:brightness-95",
    review:
      "border border-[#E0A23E] bg-[#E0A23E] text-white hover:brightness-95",
    rejected:
      "border border-[#C24B3D] bg-[#C24B3D] text-white hover:brightness-95",
    disabled:
      "border border-transparent bg-[#E3DED4] text-[#4A4F58]/60 cursor-not-allowed",
  };

  return (
    <button
      disabled={disabled || variant === "disabled"}
      className={`${base} ${variants[variant]}`}
    >
      {children}
    </button>
  );
}
```

---

## 20. Exemplo de input em React

```tsx
type CaaInputProps = {
  label: string;
  placeholder?: string;
  value?: string;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
};

export function CaaInput({ label, placeholder, value, onChange }: CaaInputProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-[0.08em] text-[#101C2C]">
        {label}
      </span>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="h-[42px] w-full rounded-[8px] border border-[#101C2C]/70 bg-transparent px-3 text-sm text-[#101C2C] placeholder:text-[#4A4F58]/70 focus:border-[#101C2C] focus:outline-none focus:ring-2 focus:ring-[#101C2C]/15"
      />
    </label>
  );
}
```

---

## 21. Exemplo de Evidence Card em React

```tsx
type EvidenceStatus = "approved" | "review" | "rejected";

type EvidenceCardProps = {
  field: string;
  value: string;
  confidence: number;
  evidence: string;
  page: number;
  status?: EvidenceStatus;
};

const statusClass = {
  approved: "bg-[#1E9E6B] text-white",
  review: "bg-[#E0A23E] text-white",
  rejected: "bg-[#C24B3D] text-white",
};

export function EvidenceCard({
  field,
  value,
  confidence,
  evidence,
  page,
  status = "approved",
}: EvidenceCardProps) {
  return (
    <article className="relative rounded-[8px] border border-[#101C2C]/70 bg-[#FAF7F0] p-5 shadow-[0_2px_6px_rgba(16,28,44,0.08)]">
      <span className="absolute left-3 top-3 h-4 w-4 border-l-2 border-t-2 border-[#101C2C]" />
      <span className="absolute bottom-3 right-3 h-4 w-4 border-b-2 border-r-2 border-[#101C2C]" />

      <div className="grid grid-cols-[92px_1fr_auto] items-center gap-3">
        <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#101C2C]">
          Field
        </span>
        <span className="text-sm text-[#4A4F58]">{field}</span>
        <span className={`rounded-[6px] px-2 py-1 font-mono text-xs font-bold ${statusClass[status]}`}>
          {confidence}%
        </span>
      </div>

      <div className="mt-3 grid grid-cols-[92px_1fr] items-center gap-3">
        <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-[#101C2C]">
          Value
        </span>
        <span className="font-mono text-sm text-[#101C2C]">{value}</span>
      </div>

      <div className="my-4 h-px bg-[#101C2C]/18" />

      <p className="border-l-2 border-[#101C2C] pl-3 text-sm text-[#4A4F58]">
        “{evidence}”
      </p>

      <div className="mt-4 inline-flex items-center rounded-[6px] border border-[#101C2C]/70 px-2.5 py-1 font-mono text-xs text-[#101C2C]">
        Page {page}
      </div>
    </article>
  );
}
```

---

## 22. Checklist para o agente de código

Antes de finalizar qualquer tela ou componente, verifique:

- [ ] O fundo usa `#F4EFE4` ou superfície derivada.
- [ ] A cor principal é `#101C2C`.
- [ ] Ícones são outline, 2px, rounded caps.
- [ ] Inputs e cards usam radius de 8px.
- [ ] Status approved/review/rejected usam as cores oficiais.
- [ ] Gradiente aparece apenas no confidence meter.
- [ ] Não há neon, glassmorphism, 3D ou sombras pesadas.
- [ ] Há whitespace generoso.
- [ ] Dados financeiros usam fonte monospace.
- [ ] O motivo de brackets aparece em pontos estratégicos, não em excesso.
- [ ] A interface parece uma ferramenta de auditoria, não uma landing page genérica.
- [ ] Componentes mantêm legibilidade em telas pequenas.
- [ ] Estados de hover/focus/disabled estão definidos.

---

## 23. Do / Don’t

### Do

- Use navy como base visual.
- Use paper background.
- Use badges de status consistentes.
- Use cards com bordas finas.
- Use brackets para elementos relacionados a evidência.
- Use monospace para dados e códigos.
- Use microinterações discretas.

### Don’t

- Não usar neon.
- Não usar robôs, cérebros ou ícones genéricos de IA.
- Não usar gradientes decorativos.
- Não usar sombras pesadas.
- Não usar muitos tons além da paleta.
- Não usar componentes arredondados demais em toda a interface.
- Não usar o wordmark completo como favicon.
- Não transformar a interface em algo “cripto”, “gamer” ou “sci-fi”.

---

## 24. Direção final

O CAA deve parecer um produto que um time de asset servicing, compliance ou operações financeiras confiaria para revisar documentos sensíveis.

A interface deve comunicar:

> “Este sistema encontra, valida e explica evidências em documentos financeiros com precisão auditável.”

Tudo no design deve reforçar essa ideia.
