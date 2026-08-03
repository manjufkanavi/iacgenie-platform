import React, { useState, useEffect } from 'react';

interface CodeLine {
  text: string;
  type?: 'prompt' | 'status' | 'code';
}

interface AnimatedCodeBlockProps {
  initialPrompt?: string;
  statusLines?: CodeLine[];
  generatedCode?: string;
  language?: 'opentofu' | 'json' | 'yaml';
  autoType?: boolean;
}

const AnimatedCodeBlock: React.FC<AnimatedCodeBlockProps> = ({
  initialPrompt = '$ generate "serverless API with DynamoDB on AWS"',
  statusLines = [
    { text: 'AI analyzing request...', type: 'status' },
    { text: '✓ Creating AWS Lambda function', type: 'status' },
    { text: '✓ Setting up DynamoDB table', type: 'status' },
    { text: '✓ Configuring API Gateway', type: 'status' },
  ],
  generatedCode = `resource "aws_lambda_function" "api" {
  runtime     = "nodejs18.x"
  handler     = "index.handler"
  role        = aws_iam_role.lambda.arn

  filename      = "lambda-function.zip"
  function_name = "serverless-api"
  timeout       = 30
  memory_size   = 128

  environment {
    variables = {
      TABLE_NAME = "api-table"
      ENVIRONMENT = "production"
    }
  }

  tags = {
    Environment = "production"
    ManagedBy   = "Iacgenie"
  }
}`,
  autoType = true,
}) => {
  const [displayedLines, setDisplayedLines] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!autoType) {
      setDisplayedLines([...statusLines.map(l => l.text), '', generatedCode]);
      setIsComplete(true);
      return;
    }

    let charIndex = 0;
    const fullLines: string[] = [];

    // Combine status lines and code into one array
    const allLines: string[] = [
      initialPrompt,
      ...statusLines.map(l => l.text),
      '',
      generatedCode,
    ];

    const typeLine = (lineIndex: number) => {
      if (lineIndex >= allLines.length) {
        setDisplayedLines(allLines);
        setIsComplete(true);
        return;
      }

      const line = allLines[lineIndex];
      
      // For code blocks, show the full line immediately (not character by character)
      if (line.startsWith('resource ') || line.startsWith('$') || line.length > 100) {
        fullLines.push(line);
        setDisplayedLines([...fullLines]);
        typeLine(lineIndex + 1);
      } else {
        // For status lines, type character by character
        if (charIndex < line.length) {
          fullLines[lineIndex] = (fullLines[lineIndex] || '') + line[charIndex];
          setDisplayedLines([...fullLines]);
          charIndex++;
          setTimeout(() => typeLine(lineIndex), 30); // 30ms per character
        } else {
          fullLines[lineIndex] = line;
          setDisplayedLines([...fullLines]);
          charIndex = 0;
          // Delay between lines (250ms)
          setTimeout(() => typeLine(lineIndex + 1), 250);
        }
      }
    };

    const timer = setTimeout(() => typeLine(0), 500);
    return () => clearTimeout(timer);
  }, [autoType, initialPrompt, statusLines, generatedCode]);

  const syntaxHighlight = (code: string) => {
    // Simple OpenTofu syntax highlighting
    const tokens = code.split(/(\s+|[{}[\]=;"])/);
    
    return tokens.map((token, index) => {
      if (token.startsWith('"') && token.endsWith('"')) {
        return <span key={index} className="text-green-400">{token}</span>;
      }
      if (token === 'resource' || token === 'variable' || token === 'output') {
        return <span key={index} className="text-purple-400">{token}</span>;
      }
      if (token === 'true' || token === 'false') {
        return <span key={index} className="text-brand-primary">{token}</span>;
      }
      if (token.startsWith('//')) {
        return <span key={index} className="text-slate-500">{token}</span>;
      }
      if (token.match(/^[A-Z]/)) {
        return <span key={index} className="text-blue-400">{token}</span>;
      }
      return <span key={index}>{token}</span>;
    });
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 font-mono text-sm shadow-xl max-w-3xl mx-auto overflow-x-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Generated Infrastructure</h3>
        <div className="flex gap-2">
          <button
            onClick={() => navigator.clipboard.writeText(generatedCode)}
            className="text-gray-400 hover:text-white transition-colors duration-200"
            title="Copy to clipboard"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
        </div>
      </div>
      
      <div className="space-y-2">
        {displayedLines.map((line, index) => (
          <div key={index} className="flex items-center">
            {line.startsWith('resource ') || line.length > 100 ? (
              <pre className="text-green-400 whitespace-pre overflow-x-auto">{syntaxHighlight(line)}</pre>
            ) : line === '' ? (
              <div className="h-4" />
            ) : (
              <span className={line.startsWith('✓') ? 'text-green-400' : line.startsWith('$') ? 'text-brand-primary' : 'text-gray-300'}>
                {line}
              </span>
            )}
          </div>
        ))}
        
        {!isComplete && (
          <span className="inline-block w-2 h-4 bg-gray-400 animate-blink ml-1" />
        )}
      </div>
    </div>
  );
};

export default AnimatedCodeBlock;