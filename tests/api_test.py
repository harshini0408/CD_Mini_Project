import urllib.request, json

code = 'ASK FOR marks\nIF marks IS GREATER THAN OR EQUAL TO 50\n    PRINT "Pass"\nELSE\n    PRINT "Fail"\nEND IF\n'

# Analyze
data = json.dumps({'code': code}).encode()
req = urllib.request.Request('http://localhost:5000/api/analyze', data=data, headers={'Content-Type':'application/json'}, method='POST')
result = json.loads(urllib.request.urlopen(req).read())
print('=== ANALYZE ===')
print('Success:', result['success'])
print('Errors:', result['errors'])
print('Tokens count:', len(result['tokens']))
print('Flowchart nodes:', list(result['flowchart']['nodes'].keys()))
print()

# Run pass
data2 = json.dumps({'code': code, 'inputs': ['75']}).encode()
req2 = urllib.request.Request('http://localhost:5000/api/run', data=data2, headers={'Content-Type':'application/json'}, method='POST')
result2 = json.loads(urllib.request.urlopen(req2).read())
print('=== RUN marks=75 ===')
print('Status:', result2['status'])
print('Output:', result2['output'])
print('Events count:', len(result2['events']))

# Run fail
data3 = json.dumps({'code': code, 'inputs': ['30']}).encode()
req3 = urllib.request.Request('http://localhost:5000/api/run', data=data3, headers={'Content-Type':'application/json'}, method='POST')
result3 = json.loads(urllib.request.urlopen(req3).read())
print()
print('=== RUN marks=30 ===')
print('Output:', result3['output'])

# Sum loop
loop_code = 'SET total TO 0\nREPEAT 5 TIMES\n    SET total TO total + 10\nEND REPEAT\nPRINT total\n'
data4 = json.dumps({'code': loop_code, 'inputs': []}).encode()
req4 = urllib.request.Request('http://localhost:5000/api/run', data=data4, headers={'Content-Type':'application/json'}, method='POST')
result4 = json.loads(urllib.request.urlopen(req4).read())
print()
print('=== SUM LOOP ===')
print('Output:', result4['output'])

# Invalid program
invalid = 'SET total TO missing + 10\nPRINT total\n'
data5 = json.dumps({'code': invalid, 'inputs': []}).encode()
req5 = urllib.request.Request('http://localhost:5000/api/run', data=data5, headers={'Content-Type':'application/json'}, method='POST')
result5 = json.loads(urllib.request.urlopen(req5).read())
print()
print('=== INVALID PROGRAM ===')
print('Status:', result5['status'])
print('Errors:', result5['errors'])
print('Output:', result5['output'])
