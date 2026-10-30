"""
LogicFlow Flask Application
Provides REST API endpoints for the frontend.
"""
import uuid
from flask import Flask, request, jsonify, render_template

from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic_analyzer import SemanticAnalyzer
from compiler.intermediate_code import IRGenerator
from compiler.interpreter import Interpreter
from compiler.flowchart_generator import FlowchartGenerator
from compiler.ast_nodes import ast_to_dict
from compiler.errors import LogicFlowError

app = Flask(__name__)

# In-memory session store for step-by-step execution
_sessions: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Built-in examples
# ---------------------------------------------------------------------------

EXAMPLES = {
    'pass_fail': {
        'name': 'A - Pass or Fail',
        'description': 'Grade check using IF/ELSE',
        'code': (
            'ASK FOR marks\n'
            'IF marks IS GREATER THAN OR EQUAL TO 50\n'
            '    PRINT "Pass"\n'
            'ELSE\n'
            '    PRINT "Fail"\n'
            'END IF\n'
        ),
    },
    'zero_check': {
        'name': 'B - Zero Check',
        'description': 'Check if a number is zero',
        'code': (
            'ASK FOR number\n'
            'IF number IS EQUAL TO 0\n'
            '    PRINT "Zero"\n'
            'ELSE\n'
            '    PRINT "Non-zero"\n'
            'END IF\n'
        ),
    },
    'sum_loop': {
        'name': 'C - Sum with Loop',
        'description': 'Sum using REPEAT loop',
        'code': (
            'SET total TO 0\n'
            'REPEAT 5 TIMES\n'
            '    SET total TO total + 10\n'
            'END REPEAT\n'
            'PRINT total\n'
        ),
    },
    'nested_condition': {
        'name': 'D - Nested Conditions',
        'description': 'Age classification with nested IF',
        'code': (
            'ASK FOR age\n'
            'IF age IS GREATER THAN OR EQUAL TO 18\n'
            '    IF age IS GREATER THAN OR EQUAL TO 60\n'
            '        PRINT "Senior"\n'
            '    ELSE\n'
            '        PRINT "Adult"\n'
            '    END IF\n'
            'ELSE\n'
            '    PRINT "Minor"\n'
            'END IF\n'
        ),
    },
    'arithmetic': {
        'name': 'E - Arithmetic Precedence',
        'description': 'Tests operator precedence (result = 20)',
        'code': (
            'SET result TO 10 + 5 * 2\n'
            'PRINT result\n'
        ),
    },
    'invalid': {
        'name': 'F - Invalid Program',
        'description': 'Demonstrates semantic error detection',
        'code': (
            'SET total TO missing + 10\n'
            'PRINT total\n'
        ),
    },
}

# ---------------------------------------------------------------------------
# Compiler pipeline helper
# ---------------------------------------------------------------------------

def _run_pipeline(source: str) -> dict:
    """Run lexer → parser → semantic analyzer → IR → flowchart.
    Returns a dict with all compiler artifacts and any errors.
    """
    result = {
        'tokens': [],
        'ast': None,
        'symbol_table': {},
        'intermediate_code': [],
        'intermediate_text': '',
        'flowchart': {'mermaid': '', 'nodes': {}},
        'errors': [],
        'success': False,
        'program': None,  # internal
    }

    # --- Lexing ---
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    result['tokens'] = [t.to_dict() for t in tokens]
    if lexer.errors:
        result['errors'].extend([e.to_dict() for e in lexer.errors])
        # Continue parsing even with lexer errors

    # --- Parsing ---
    parser = Parser(tokens)
    program = parser.parse()
    result['ast'] = ast_to_dict(program)
    if parser.errors:
        result['errors'].extend([e.to_dict() for e in parser.errors])
        return result  # Cannot proceed without a valid parse

    # --- Semantic Analysis ---
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    result['symbol_table'] = analyzer.symbol_table.to_dict()
    if analyzer.errors:
        result['errors'].extend([e.to_dict() for e in analyzer.errors])
        return result  # Do not execute invalid programs

    # --- IR Generation ---
    ir_gen = IRGenerator()
    instructions = ir_gen.generate(program)
    result['intermediate_code'] = ir_gen.instructions_as_dicts()
    result['intermediate_text'] = ir_gen.instructions_as_text()

    # --- Flowchart ---
    fc_gen = FlowchartGenerator()
    flowchart = fc_gen.generate(program)
    result['flowchart'] = flowchart

    result['success'] = True
    result['program'] = program  # keep for execution
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/examples', methods=['GET'])
def get_examples():
    return jsonify({k: {kk: vv for kk, vv in v.items() if kk != 'code'} | {'code': v['code']}
                    for k, v in EXAMPLES.items()})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True)
    if not data or 'code' not in data:
        return jsonify({'error': 'Missing code field'}), 400

    source = data['code']
    result = _run_pipeline(source)
    result.pop('program', None)
    return jsonify(result)


@app.route('/api/run', methods=['POST'])
def run():
    data = request.get_json(silent=True)
    if not data or 'code' not in data:
        return jsonify({'error': 'Missing code field'}), 400

    source = data['code']
    inputs = data.get('inputs', [])

    pipeline = _run_pipeline(source)
    if not pipeline['success']:
        return jsonify({
            'status': 'error',
            'output': [],
            'events': [],
            'variables': {},
            'errors': pipeline['errors'],
            'flowchart': pipeline['flowchart'],
            'waiting_for': None,
        })

    program = pipeline['program']
    interpreter = Interpreter(inputs=inputs)
    exec_result = interpreter.execute(program)

    return jsonify({
        'status': exec_result['status'],
        'output': exec_result['output'],
        'events': exec_result['events'],
        'variables': exec_result['variables'],
        'errors': [{'category': 'Runtime Error', 'message': e, 'line': None, 'column': None}
                   for e in exec_result['errors']],
        'flowchart': pipeline['flowchart'],
        'waiting_for': exec_result.get('waiting_for'),
    })


@app.route('/api/step', methods=['POST'])
def step():
    """
    Simple step execution: compile the program and return events one at a time
    using a session state keyed by session_id.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Missing body'}), 400

    session_id = data.get('session_id')
    if not session_id or session_id not in _sessions:
        # Create new session
        source = data.get('code', '')
        inputs = data.get('inputs', [])
        pipeline = _run_pipeline(source)
        if not pipeline['success']:
            return jsonify({'status': 'error', 'errors': pipeline['errors']})
        interp = Interpreter(inputs=inputs)
        exec_result = interp.execute(pipeline['program'])
        session_id = str(uuid.uuid4())
        _sessions[session_id] = {
            'events': exec_result['events'],
            'event_index': 0,
            'output': exec_result['output'],
            'variables': exec_result['variables'],
            'status': exec_result['status'],
            'flowchart': pipeline['flowchart'],
            'errors': exec_result['errors'],
        }

    sess = _sessions[session_id]
    idx = sess['event_index']
    events = sess['events']

    if idx >= len(events):
        return jsonify({
            'session_id': session_id,
            'status': 'completed',
            'done': True,
            'event': None,
            'output': sess['output'],
            'variables': sess['variables'],
            'flowchart': sess['flowchart'],
        })

    event = events[idx]
    sess['event_index'] = idx + 1

    return jsonify({
        'session_id': session_id,
        'status': 'stepping',
        'done': idx + 1 >= len(events),
        'event': event,
        'event_index': idx,
        'total_events': len(events),
        'output': sess['output'][:],
        'variables': sess['variables'],
        'flowchart': sess['flowchart'],
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    return jsonify({'status': 'reset'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
