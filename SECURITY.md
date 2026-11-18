# Local credentials and upload boundaries

The API keeps authentication enabled. Actual keys are generated locally in `.runtime/api_key.txt` or supplied through `CF384_API_KEY`. Do not commit these values. The header name `X-API-Key` and key-generation code are public interface definitions, not credentials.

`.gitignore` excludes runtime secrets, environment files, virtualenvs, logs, private keys, model downloads, image samples and archives. Ignore rules do not remove files already committed; inspect the staged diff before future pushes.

This repository snapshot contains source, documentation, small trained heads, provenance and OpenAPI definitions. It does not contain the original photo/evaluation datasets, actual runtime keys, local HTTP logs, absolute personal filesystem paths or the large CF384 backbone. The latter is downloaded from the pinned official revision and verified with SHA256.

Use loopback binding by default. Restrict extension Origin IDs when known. Do not put API keys into a page DOM, URLs or public screenshots. The default HTTP development service is not an Internet-facing TLS deployment.
