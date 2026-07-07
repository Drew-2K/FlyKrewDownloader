// Validates the inline <script> in static/index.html parses as valid JS.
// Catches syntax errors before they ship to the browser.
const fs = require('fs');

const html = fs.readFileSync('static/index.html', 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) {
	console.error('No inline <script> block found in static/index.html');
	process.exit(1);
}

try {
	new Function(match[1]); // parse only; does not execute
	console.log('Inline JS syntax OK');
} catch (err) {
	console.error('Inline JS syntax error:', err.message);
	process.exit(1);
}
