# LogicFlow 🔀

**An English-Like Programming Language with Automatic Flowchart Generation and Execution**

> Write Logic. See the Flow.

---

## 1. Project Overview

LogicFlow is a visual programming environment built as a Compiler Design mini-project.
Users write programs in a small, structured, English-like language. The system automatically:

1. Performs **lexical analysis** (tokenisation)
2. **Parses** the source via a recursive-descent parser
3. Builds a genuine **Abstract Syntax Tree (AST)**
4. Runs **semantic validation** before execution
5. Generates an **intermediate representation** (stack-machine instructions)
6. Creates an **AST-driven flowchart** (Mermaid.js)
7. **Executes** the program step by step
8. **Highlights** the actual execution path on the flowchart

---

## 2. Problem Statement

Traditional programming courses teach compilation theory abstractly. Students struggle to connect lexer→parser→AST→execution to something they can see and interact with. LogicFlow bridges this gap by making every compilation stage visible and interactive.

---

## 3. Objectives

- Design and implement a formally specified mini-language
- Build a complete compiler pipeline (lexer → parser → AST → semantic analysis → IR → interpreter)
- Auto-generate control-flow diagrams directly from the AST
- Highlight the actual runtime execution path on the diagram
- Provide an interactive web IDE suitable for classroom demonstration

---

## 4. Features

| Feature | Status |
|---|---|
| Handwritten lexer | ✅ |
| Recursive-descent parser | ✅ |
| Genuine AST (dataclasses) | ✅ |
| Semantic analysis + symbol table | ✅ |
| Stack-machine IR | ✅ |
| AST-driven flowchart (Mermaid.js) | ✅ |
| Execution-path highlighting | ✅ |
| Step-by-step execution | ✅ |
| ASK FOR (user input) | ✅ |
| Nested IF/ELSE | ✅ |
| REPEAT loops | ✅ |
| Operator precedence | ✅ |
| Comments (`#`) | ✅ |
| 6 built-in examples | ✅ |
| 69 automated tests | ✅ |
| Dark IDE web interface | ✅ |

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask |
| Compiler | Handwritten lexer + recursive-descent parser |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Flowchart | Mermaid.js 10 |
| Data exchange | JSON REST API |
| Testing | pytest / unittest |

---

## 6. Language Syntax

### Input
```
ASK FOR marks
ASK FOR name
```

### Output
```
PRINT "Hello, World!"
PRINT marks
PRINT marks + 10
```

### Assignment
```
SET age TO 18
SET total TO marks + 15
```

### Arithmetic
```
SET result TO 10 + 5 * 2      # → 20 (precedence)
SET r TO (10 + 5) * 2         # → 30 (parentheses)
```
Operators: `+  -  *  /  %`

### Conditionals
```
IF marks IS GREATER THAN OR EQUAL TO 50
    PRINT "Pass"
ELSE
    PRINT "Fail"
END IF
```

Comparison phrases:
- `IS EQUAL TO`
- `IS NOT EQUAL TO`
- `IS GREATER THAN`
- `IS LESS THAN`
- `IS GREATER THAN OR EQUAL TO`
- `IS LESS THAN OR EQUAL TO`

### Loops
```
REPEAT 5 TIMES
    SET total TO total + 10
END REPEAT
```

### Comments
```
# This is a comment
```

---

## 7. EBNF Grammar

```ebnf
program          = { statement } EOF ;
statement        = inputStatement
                 | printStatement
                 | assignment
                 | ifStatement
                 | repeatStatement ;

inputStatement   = "ASK FOR" identifier NEWLINE ;
assignment       = "SET" identifier "TO" expression NEWLINE ;
printStatement   = "PRINT" expression NEWLINE ;

ifStatement      = "IF" condition NEWLINE
                     block
                   [ "ELSE" NEWLINE block ]
                   "END IF" NEWLINE ;

repeatStatement  = "REPEAT" expression "TIMES" NEWLINE
                     block
                   "END REPEAT" NEWLINE ;

condition        = expression comparisonOp expression ;
comparisonOp     = "IS EQUAL TO" | "IS NOT EQUAL TO"
                 | "IS GREATER THAN" | "IS LESS THAN"
                 | "IS GREATER THAN OR EQUAL TO"
                 | "IS LESS THAN OR EQUAL TO" ;

expression       = term { ( "+" | "-" ) term } ;
term             = factor { ( "*" | "/" | "%" ) factor } ;
factor           = NUMBER | STRING | identifier
                 | "(" expression ")" | "-" factor ;

block            = { statement } ;
identifier       = LETTER { LETTER | DIGIT | "_" } ;
```

---

## 8. Compiler Architecture

```
Source Code
    │
    ▼
┌─────────┐
│  Lexer  │  → Token stream (tokens.py, lexer.py)
└─────────┘
    │
    ▼
┌─────────┐
│ Parser  │  → AST (parser.py, ast_nodes.py)
└─────────┘
    │
    ▼
┌──────────────────┐
│ Semantic Analyzer│  → Symbol table, error list (semantic_analyzer.py)
└──────────────────┘
    │
    ├──────────────────────────┐
    ▼                          ▼
┌────────────┐        ┌───────────────────┐
│ IR Generator│        │ Flowchart Generator│
│(3-addr code)│        │ (Mermaid.js output)│
└────────────┘        └───────────────────┘
    │
    ▼
┌─────────────┐
│ Interpreter │  → Output, events, variable state
└─────────────┘
```

### Stage 1 – Lexical Analysis

The lexer (`lexer.py`) converts raw text to a token stream.
Multi-word keywords (e.g., `IS GREATER THAN OR EQUAL TO`) are assembled in a second pass using a longest-match pattern table.

Each token carries: `type`, `value`, `line`, `column`.

### Stage 2 – Syntax Analysis

A recursive-descent parser (`parser.py`) consumes the token stream and produces an AST.
It reports meaningful errors for missing block terminators and malformed expressions.

### Stage 3 – AST

Python `dataclasses` represent each node type:
`Program`, `InputStatement`, `PrintStatement`, `Assignment`, `NumberLiteral`, `StringLiteral`, `VariableReference`, `BinaryExpression`, `ComparisonExpression`, `IfStatement`, `RepeatStatement`.

Every node has a stable `node_id` used for flowchart mapping.

### Stage 4 – Semantic Analysis

The semantic analyzer (`semantic_analyzer.py`) walks the AST and:
- Detects undefined variables
- Detects literal division by zero
- Detects negative literal repeat counts
- Maintains a symbol table with inferred types
- Variables declared by `ASK FOR` have type `any` (runtime type depends on user input)

Programs with semantic errors **do not execute**.

### Stage 5 – Intermediate Representation

`IRGenerator` produces a stack-machine instruction sequence:
```
PROGRAM_START
LOAD_CONST 10
STORE x
LOAD x
LOAD_CONST 5
ADD
STORE y
LOAD y
PRINT
PROGRAM_END
```

Conditional branches use `JUMP_IF_FALSE <label>` and `JUMP <label>`.
Loops use a counter variable and back-jump.

### Stage 6 – Execution Engine

The interpreter (`interpreter.py`) executes the AST directly.
- No `eval()` or `exec()` used anywhere
- Emits `ExecutionEvent` objects (`enter_node`, `branch`, `loop_iteration`, etc.) keyed by node ID
- Input pauses emit `waiting_input` status
- Enforces `MAX_STATEMENTS = 10,000` and `MAX_LOOP_ITERATIONS = 1,000`

### Stage 7 – Flowchart Generation

`FlowchartGenerator` traverses the AST and produces:
- Mermaid.js `flowchart TD` syntax
- Node metadata map: `node_id → {label, shape_class}`

Shapes used:
| Node type | Shape |
|---|---|
| Start/End | Rounded (`([…])`) |
| Process/Assignment | Rectangle (`[…]`) |
| Input/Output | Parallelogram (`[/…/]`) |
| Decision | Diamond (`{…}`) |
| Loop entry | Rectangle + synthetic decision |

---

## 9. Flowchart Highlighting Algorithm

1. Backend runs the program and returns an ordered list of `ExecutionEvent` objects
2. Each event carries the `node_id` of the node being executed
3. Frontend calls `highlightExecutionPath(events)`:
   - All visited node IDs get green stroke (`node-visited`)
   - The final active node gets orange glow (`node-active`)
4. For step mode, each event is applied individually after each `/api/step` call

The highlighting is driven entirely by backend events — no path guessing in JavaScript.

---

## 10. Difference: Compiler vs Interpreter vs Flowchart Generator

| Concept | Definition | LogicFlow stage |
|---|---|---|
| **Compiler** | Translates source to target language (e.g., machine code) | Lexer + Parser + Semantic + IR |
| **Interpreter** | Executes source/AST directly without generating machine code | AST Interpreter |
| **Flowchart Generator** | Converts control-flow structure to visual diagram | AST → Mermaid.js |

LogicFlow is an **educational language processor**: it implements all traditional compiler front-end stages (lexing, parsing, semantic analysis, IR generation) but interprets the AST instead of generating native machine code. This is appropriate for a college Compiler Design project.

---

## 11. Installation

```bash
# 1. Clone / navigate to project
cd logicflow

# 2. (Optional) create a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## 12. Running Tests

```bash
python -m pytest tests/ -v
```

Expected: **69 tests pass**.

---

## 13. Example Programs

### A – Pass or Fail
```
ASK FOR marks
IF marks IS GREATER THAN OR EQUAL TO 50
    PRINT "Pass"
ELSE
    PRINT "Fail"
END IF
```

### B – Zero Check
```
ASK FOR number
IF number IS EQUAL TO 0
    PRINT "Zero"
ELSE
    PRINT "Non-zero"
END IF
```

### C – Sum with Loop
```
SET total TO 0
REPEAT 5 TIMES
    SET total TO total + 10
END REPEAT
PRINT total
```
Expected output: `50`

### D – Nested Conditions
```
ASK FOR age
IF age IS GREATER THAN OR EQUAL TO 18
    IF age IS GREATER THAN OR EQUAL TO 60
        PRINT "Senior"
    ELSE
        PRINT "Adult"
    END IF
ELSE
    PRINT "Minor"
END IF
```

### E – Arithmetic Precedence
```
SET result TO 10 + 5 * 2
PRINT result
```
Expected output: `20`

### F – Invalid Program (semantic error)
```
SET total TO missing + 10
PRINT total
```
Expected: Semantic error for undefined variable `missing`. Program does not execute.

---

## 14. Known Limitations

- No `ELSE IF` / `ELIF` chain (only nested `IF` inside `ELSE`)
- No logical `AND` / `OR` in conditions
- No string comparison (only numeric comparisons)
- No arrays or functions
- Step mode uses pre-computed events, not true pause/resume coroutines
- Mermaid.js node highlighting depends on its internal SVG `id` attribute format

---

## 15. Future Enhancements

- `ELSE IF` syntax
- `AND` / `OR` logical operators
- String comparison
- User-defined functions / procedures
- While loops (`WHILE condition DO … END WHILE`)
- Type annotations
- Export flowchart as PNG/SVG
- Syntax highlighting in the editor (CodeMirror)
- True coroutine-based step execution

---

## 16. Project Structure

```
logicflow/
├── app.py                      Flask application + API endpoints
├── requirements.txt
├── README.md
├── compiler/
│   ├── __init__.py
│   ├── tokens.py               Token types and Token class
│   ├── lexer.py                Handwritten lexer
│   ├── parser.py               Recursive-descent parser
│   ├── ast_nodes.py            AST node dataclasses
│   ├── semantic_analyzer.py    Semantic validation
│   ├── symbol_table.py         Variable tracking
│   ├── intermediate_code.py    IR generator
│   ├── interpreter.py          AST interpreter + event emitter
│   ├── flowchart_generator.py  AST → Mermaid.js
│   └── errors.py               Error hierarchy
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── tests/
    ├── test_lexer.py
    ├── test_parser.py
    ├── test_semantic.py
    ├── test_interpreter.py
    └── test_flowchart.py
```

---

*LogicFlow — Compiler Design Mini-Project*
