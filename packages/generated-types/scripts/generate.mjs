import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(packageRoot, "../..");
const apiRoot = resolve(repositoryRoot, "apps/api-server");
const python = resolve(apiRoot, "venv/bin/python");
const output = resolve(packageRoot, "src/api.ts");

const rawSchema = execFileSync(
  python,
  [
    "-c",
    "import json; from main import app; print(json.dumps(app.openapi()))",
  ],
  {
    cwd: apiRoot,
    encoding: "utf8",
  },
);

const ast = await openapiTS(JSON.parse(rawSchema));
mkdirSync(dirname(output), { recursive: true });
writeFileSync(
  output,
  `// Generated from apps/api-server FastAPI OpenAPI. Do not edit.\n${astToString(ast)}`,
);
