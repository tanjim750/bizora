import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('SF-01 Setup & Tooling', () => {
  it('pins dependencies and devDependencies to exact versions and has all required scripts', () => {
    const pkgPath = path.resolve(process.cwd(), 'package.json');
    expect(fs.existsSync(pkgPath)).toBe(true);

    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    const exactVersionRegex = /^\d+\.\d+\.\d+$/;

    for (const [dep, version] of Object.entries(pkg.dependencies || {})) {
      expect(version, `dependency ${dep} should be exact version`).toMatch(exactVersionRegex);
    }

    for (const [dep, version] of Object.entries(pkg.devDependencies || {})) {
      expect(version, `devDependency ${dep} should be exact version`).toMatch(exactVersionRegex);
    }

    expect(pkg.dependencies.next).toBe('16.4.6');
    expect(pkg.dependencies.react).toBe('19.3.1');
    expect(pkg.devDependencies.typescript).toBe('5.9.3');
    expect(pkg.dependencies.motion).toBe('14.14.0');
    expect(pkg.dependencies.gsap).toBe('3.15.1');

    const expectedScripts = [
      'dev',
      'build',
      'start',
      'test',
      'typecheck',
      'lint',
      'format:check',
      'test:e2e',
      'contract:check',
    ];
    for (const script of expectedScripts) {
      expect(pkg.scripts[script], `script ${script} must exist`).toBeDefined();
    }
  });

  it('has strict tsconfig.json with correct paths mapping', () => {
    const tsconfigPath = path.resolve(process.cwd(), 'tsconfig.json');
    expect(fs.existsSync(tsconfigPath), 'tsconfig.json must exist').toBe(true);

    const tsconfig = JSON.parse(fs.readFileSync(tsconfigPath, 'utf8'));
    expect(tsconfig.compilerOptions.strict).toBe(true);
    expect(tsconfig.compilerOptions.paths['@/*']).toEqual(['./src/*']);
  });

  it('has .env.example with required configuration keys', () => {
    const envExamplePath = path.resolve(process.cwd(), '.env.example');
    expect(fs.existsSync(envExamplePath), '.env.example must exist').toBe(true);

    const envContent = fs.readFileSync(envExamplePath, 'utf8');
    const lines = envContent.split('\n');

    expect(lines.some((l) => l.startsWith('API_BASE_URL='))).toBe(true);
    expect(lines.some((l) => l.startsWith('NEXT_PUBLIC_SITE_URL='))).toBe(true);
    expect(lines.some((l) => l.startsWith('MOCK_LATENCY_MS='))).toBe(true);
    expect(lines.some((l) => l.startsWith('IMAGE_REMOTE_HOST='))).toBe(true);
  });

  it('has all required configuration and entrypoint files', () => {
    const requiredFiles = [
      'next.config.ts',
      'eslint.config.mjs',
      'postcss.config.mjs',
      '.prettierrc.json',
      'src/app/layout.tsx',
      'src/app/(store)/page.tsx',
    ];

    for (const file of requiredFiles) {
      const filePath = path.resolve(process.cwd(), file);
      expect(fs.existsSync(filePath), `file ${file} must exist`).toBe(true);
    }
  });
});
