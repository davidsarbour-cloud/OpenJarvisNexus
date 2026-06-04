@echo off
REM Dependency Cruiser Audit Report (npm devDependency, not the old 283MB clone)
node .\frontend\node_modules\dependency-cruiser\bin\dependency-cruise.mjs --no-config --output-type text frontend/src > dependency-audit-report.txt
echo Report generated: dependency-audit-report.txt
