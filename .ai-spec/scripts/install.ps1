[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetRoot,

    [ValidateSet('auto', 'new', 'existing', 'in-progress')]
    [string]$Mode = 'auto',

    [string[]]$Tools = @('generic'),

    [switch]$Apply,

    [switch]$Onboard,

    [switch]$Sync,

    [switch]$ManageGit,

    [ValidateSet('auto', 'parent', 'projects', 'none')]
    [string]$GitScope = 'auto',

    [string]$BranchName = 'chore/specforge-onboard'
)

$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$targetFullPath = [System.IO.Path]::GetFullPath($TargetRoot)
$validTools = @('generic', 'claude-code', 'codex', 'cursor', 'github-copilot')
$Tools = @($Tools | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
$invalidTools = @($Tools | Where-Object { $_ -notin $validTools })
if ($invalidTools.Count -gt 0) {
    throw "Unsupported tool adapter: $($invalidTools -join ', '). Use generic for unknown tools."
}

if (-not (Test-Path -LiteralPath $targetFullPath -PathType Container)) {
    throw "Target project directory does not exist: $targetFullPath"
}

$forbiddenGlobalRoots = @(
    (Join-Path $HOME '.claude'),
    (Join-Path $HOME '.codex'),
    (Join-Path $HOME '.cursor'),
    (Join-Path $HOME '.agents')
) | ForEach-Object { [System.IO.Path]::GetFullPath($_).TrimEnd('\') }
foreach ($forbiddenRoot in $forbiddenGlobalRoots) {
    if ($targetFullPath.Equals($forbiddenRoot, [StringComparison]::OrdinalIgnoreCase) -or
        $targetFullPath.StartsWith($forbiddenRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "SpecForge is project-only and cannot target user-global AI configuration: $targetFullPath"
    }
}

if ($targetFullPath -eq [System.IO.Path]::GetFullPath($sourceRoot)) {
    throw 'Target project cannot be the template source directory.'
}

$actions = [System.Collections.Generic.List[string]]::new()
$conflicts = [System.Collections.Generic.List[string]]::new()
$installReports = [System.Collections.Generic.List[hashtable]]::new()
$coreSkills = @('product-architect', 'dev-implementation', 'code-reviewer', 'debugger', 'spec-evaluator')

function Get-TemplateVersion {
    $examplePath = Join-Path $sourceRoot 'ai-spec.example.yaml'
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $examplePath
    $match = [regex]::Match($content, '(?m)^  templateVersion:\s*(\d+)')
    if (-not $match.Success) {
        throw 'Cannot determine SpecForge templateVersion from ai-spec.example.yaml'
    }
    return [int]$match.Groups[1].Value
}

$templateVersion = Get-TemplateVersion

function Read-FileIfExists {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return (Get-Content -Raw -Encoding UTF8 -LiteralPath $Path)
    }
    return ''
}

function Test-PathAny {
    param([string]$RootDir, [string[]]$RelativePaths)
    foreach ($relativePath in $RelativePaths) {
        if (Test-Path -LiteralPath (Join-Path $RootDir $relativePath)) { return $true }
    }
    return $false
}

function Detect-Mode {
    param([string]$ProjectRoot)

    $gitDirectory = Join-Path $ProjectRoot '.git'
    if (Test-Path -LiteralPath $gitDirectory) {
        try {
            $status = & git -C $ProjectRoot status --short 2>$null
            if ($status) { return 'in-progress' }
        }
        catch { }
    }

    $signals = @(
        'package.json', 'pom.xml', 'build.gradle', 'build.gradle.kts',
        'pyproject.toml', 'requirements.txt', 'go.mod', 'Cargo.toml',
        'composer.json', 'mix.exs', 'src', 'app', 'backend', 'frontend'
    )
    foreach ($signal in $signals) {
        if (Test-Path -LiteralPath (Join-Path $ProjectRoot $signal)) {
            return 'existing'
        }
    }

    return 'new'
}

function Detect-SubProjects {
    param([string]$RootDir)

    $buildFiles = @(
        'package.json', 'pom.xml', 'go.mod', 'Cargo.toml',
        'requirements.txt', 'pyproject.toml', 'Makefile',
        'build.gradle', 'build.gradle.kts', 'composer.json',
        'mix.exs', 'CMakeLists.txt', 'BUILD', 'WORKSPACE'
    )
    $sourceDirs = @('src', 'app', 'lib')

    $projects = [System.Collections.Generic.List[hashtable]]::new()
    $children = Get-ChildItem -LiteralPath $RootDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch '^\.' -and $_.Name -notin @('node_modules', 'vendor') }

    foreach ($child in $children) {
        $isProject = $false
        $foundBuildFiles = [System.Collections.Generic.List[string]]::new()

        foreach ($buildFile in $buildFiles) {
            if (Test-Path -LiteralPath (Join-Path $child.FullName $buildFile)) {
                $isProject = $true
                $null = $foundBuildFiles.Add($buildFile)
            }
        }
        foreach ($sourceDir in $sourceDirs) {
            if (Test-Path -LiteralPath (Join-Path $child.FullName $sourceDir) -PathType Container) {
                $isProject = $true
            }
        }

        if ($isProject) {
            $projects.Add(@{
                path = $child.FullName
                name = $child.Name
                buildFiles = @($foundBuildFiles)
            })
        }
    }

    return @($projects)
}

function Test-ParentGitScopeSignal {
    param([string]$RootDir)

    if (Test-Path -LiteralPath (Join-Path $RootDir '.git')) {
        return $true
    }

    $parentSignals = @(
        'package.json', 'pnpm-workspace.yaml', 'rush.json', 'lerna.json',
        'nx.json', 'turbo.json', 'go.work', 'pom.xml', 'build.gradle',
        'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts',
        'Cargo.toml', 'Makefile', 'pyproject.toml'
    )
    return (Test-PathAny -RootDir $RootDir -RelativePaths $parentSignals)
}

function Detect-ProjectType {
    param([string]$ProjectRoot)

    if (Test-PathAny -RootDir $ProjectRoot -RelativePaths @('pubspec.yaml', 'android', 'ios')) {
        return 'mobile'
    }

    $packageJson = (Read-FileIfExists -Path (Join-Path $ProjectRoot 'package.json')).ToLowerInvariant()
    if ($packageJson) {
        $hasFrontend = $packageJson -match '"(react|vue|@angular/core|next|nuxt|svelte|vite)"'
        $hasBackend = $packageJson -match '"(express|fastify|@nestjs/core|koa|hapi)"'
        if ($hasFrontend -and $hasBackend) { return 'fullstack' }
        if ($hasFrontend) { return 'frontend' }
        if ($hasBackend) { return 'backend' }
        return 'frontend'
    }

    $pythonSignals = ((Read-FileIfExists -Path (Join-Path $ProjectRoot 'requirements.txt')) + "`n" + (Read-FileIfExists -Path (Join-Path $ProjectRoot 'pyproject.toml'))).ToLowerInvariant()
    if ($pythonSignals.Trim()) {
        if ($pythonSignals -match '(openai|anthropic|litellm|pydantic-ai|semantic-kernel|langchain|llama-index|llamaindex|transformers|sentence-transformers|chromadb|faiss)') {
            return 'ai-llm'
        }
        return 'backend'
    }

    if (Test-PathAny -RootDir $ProjectRoot -RelativePaths @('pom.xml', 'build.gradle', 'build.gradle.kts', 'go.mod', 'composer.json', 'mix.exs')) {
        return 'backend'
    }

    if (Test-PathAny -RootDir $ProjectRoot -RelativePaths @('Cargo.toml', 'CMakeLists.txt', 'BUILD', 'WORKSPACE')) {
        return 'library-sdk'
    }

    if (Test-PathAny -RootDir $ProjectRoot -RelativePaths @('bin', '__main__.py', 'main.go', 'main.rs')) {
        return 'cli'
    }

    return 'generic'
}

function Get-StackFilesForType {
    param([string]$ProjectType)

    switch ($ProjectType) {
        'frontend' { return @('frontend-general.md') }
        'backend' { return @('backend-general.md') }
        'fullstack' { return @('frontend-general.md', 'backend-general.md') }
        'mobile' { return @('mobile-general.md') }
        'library-sdk' { return @('cli.md') }
        'cli' { return @('cli.md') }
        'data-platform' { return @('data-platform.md') }
        'ai-llm' { return @('ai-llm-app.md') }
        default { return @('ai-llm-app.md', 'backend-general.md', 'cli.md', 'data-platform.md', 'frontend-general.md', 'mobile-general.md') }
    }
}

function Add-FileFromSource {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (Test-Path -LiteralPath $Destination) {
        $script:conflicts.Add($Destination)
        return
    }

    $script:actions.Add("CREATE $Destination")
    if ($Apply) {
        $parent = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $Source -Destination $Destination
    }
}

function Add-RenderedFile {
    param(
        [string]$Source,
        [string]$Destination,
        [hashtable]$Variables
    )

    if (Test-Path -LiteralPath $Destination) {
        $script:conflicts.Add($Destination)
        return
    }

    $script:actions.Add("CREATE $Destination")
    if ($Apply) {
        $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $Source
        foreach ($key in $Variables.Keys) {
            $content = $content.Replace("{{$key}}", [string]$Variables[$key])
        }
        $parent = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        [System.IO.File]::WriteAllText($Destination, $content, [System.Text.UTF8Encoding]::new($false))
    }
}

function Remove-SpecPath {
    param(
        [string]$SpecRoot,
        [string]$RelativePath,
        [string]$Reason
    )

    $specFull = [System.IO.Path]::GetFullPath($SpecRoot).TrimEnd('\', '/')
    $target = Join-Path $SpecRoot $RelativePath
    $targetFull = [System.IO.Path]::GetFullPath($target)
    $separator = [System.IO.Path]::DirectorySeparatorChar
    if (-not ($targetFull -eq $specFull -or $targetFull.StartsWith($specFull + $separator))) {
        throw "Refusing to remove path outside .ai-spec: $targetFull"
    }

    if (Test-Path -LiteralPath $targetFull) {
        $script:actions.Add("REMOVE $targetFull ($Reason)")
        if ($Apply) {
            Remove-Item -LiteralPath $targetFull -Recurse -Force
        }
    }
}

function New-AiSpecProfileContent {
    param(
        [string]$ProjectRoot,
        [string]$Stage,
        [string]$ProjectType,
        [string]$MultiProjectId
    )

    $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $sourceRoot 'ai-spec.example.yaml')
    $projectName = Split-Path -Leaf $ProjectRoot
    $multiValue = if ($MultiProjectId) { $MultiProjectId } else { 'null' }
    $toolsValue = '[' + ($Tools -join ', ') + ']'
    $inventory = Get-ProjectInventory -ProjectRoot $ProjectRoot -IsMultiProject ([bool]$MultiProjectId)
    $inference = Get-ProjectProfileInference -ProjectRoot $ProjectRoot

    $profile = $profile -replace '(?m)^  multiProjectId: null.*$', "  multiProjectId: $multiValue       # multi-project shared ID"
    $profile = $profile -replace '(?m)^  templateVersion:\s*\d+.*$', "  templateVersion: $templateVersion         # installed SpecForge template version"
    $profile = $profile -replace 'name: example-project', "name: $projectName"
    $profile = $profile -replace 'stage: new # new \| existing \| in-progress', "stage: $Stage # new | existing | in-progress"
    $profile = $profile -replace 'type: generic # backend \| frontend \| fullstack \| mobile \| library-sdk \| cli \| data-platform \| ai-llm \| generic', "type: $ProjectType # backend | frontend | fullstack | mobile | library-sdk | cli | data-platform | ai-llm | generic"
    $profile = $profile -replace 'languages: \[\]', "languages: $($inference.languages)"
    $profile = $profile -replace 'frameworks: \[\]', "frameworks: $($inference.frameworks)"
    $profile = $profile -replace 'databases: \[\]', "databases: $($inference.databases)"
    $profile = $profile -replace 'packageManagers: \[\]', "packageManagers: $($inference.packageManagers)"
    $profile = $profile -replace 'build: null', "build: $($inference.commands.build)"
    $profile = $profile -replace 'test: null', "test: $($inference.commands.test)"
    $profile = $profile -replace 'lint: null', "lint: $($inference.commands.lint)"
    $profile = $profile -replace 'typecheck: null', "typecheck: $($inference.commands.typecheck)"
    $profile = $profile -replace 'run: null', "run: $($inference.commands.run)"
    $profile = $profile -replace 'tools: \[generic\]', "tools: $toolsValue"
    $profile = $profile -replace 'projectSize: auto # auto \| tiny \| small \| medium \| large \| enterprise', "projectSize: $($inventory.projectSize) # auto | tiny | small | medium | large | enterprise"
    $profile = $profile -replace 'fileCount: 0', "fileCount: $($inventory.fileCount)"
    $profile = $profile -replace 'buildFileCount: 0', "buildFileCount: $($inventory.buildFileCount)"
    $profile = $profile -replace 'hasDatabase: false', "hasDatabase: $($inventory.hasDatabase.ToString().ToLowerInvariant())"
    $profile = $profile -replace 'hasApi: false', "hasApi: $($inventory.hasApi.ToString().ToLowerInvariant())"
    $profile = $profile -replace 'hasAuth: false', "hasAuth: $($inventory.hasAuth.ToString().ToLowerInvariant())"
    $profile = $profile -replace 'hasCi: false', "hasCi: $($inventory.hasCi.ToString().ToLowerInvariant())"
    $profile = $profile -replace 'multiProject: false', "multiProject: $($inventory.multiProject.ToString().ToLowerInvariant())"

    return $profile
}

function Write-AiSpecProfile {
    param(
        [string]$SpecRoot,
        [string]$ProjectRoot,
        [string]$Stage,
        [string]$ProjectType,
        [string]$MultiProjectId
    )

    $profileDestination = Join-Path $SpecRoot 'ai-spec.yaml'
    if (Test-Path -LiteralPath $profileDestination) {
        $script:conflicts.Add($profileDestination)
        return
    }

    $script:actions.Add("CREATE $profileDestination")
    if ($Apply) {
        $profile = New-AiSpecProfileContent -ProjectRoot $ProjectRoot -Stage $Stage -ProjectType $ProjectType -MultiProjectId $MultiProjectId
        [System.IO.File]::WriteAllText($profileDestination, $profile, [System.Text.UTF8Encoding]::new($false))
    }
}

function Add-AdapterEntrypoints {
    param([string]$ProjectRoot)

    $variables = @{
        'PROJECT_NAME' = (Split-Path -Leaf $ProjectRoot)
        'AI_SPEC_PATH' = '.ai-spec'
    }

    foreach ($tool in ($Tools | Select-Object -Unique)) {
        switch ($tool) {
            'claude-code' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\claude-code\CLAUDE.md.template') -Destination (Join-Path $ProjectRoot 'CLAUDE.md') -Variables $variables
                Add-FileFromSource -Source (Join-Path $sourceRoot 'adapters\claude-code\settings.json.template') -Destination (Join-Path $ProjectRoot '.claude\settings.json')
                foreach ($skill in $coreSkills) {
                    $sourceSkill = Join-Path $sourceRoot "skills\$skill"
                    Get-ChildItem -LiteralPath $sourceSkill -Recurse -File | ForEach-Object {
                        $skillRelative = $_.FullName.Substring($sourceSkill.Length + 1)
                        Add-FileFromSource -Source $_.FullName -Destination (Join-Path $ProjectRoot ".claude\skills\$skill\$skillRelative")
                    }
                }
            }
            'codex' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\codex\AGENTS.md.template') -Destination (Join-Path $ProjectRoot 'AGENTS.md') -Variables $variables
                foreach ($skill in $coreSkills) {
                    $sourceSkill = Join-Path $sourceRoot "skills\$skill"
                    Get-ChildItem -LiteralPath $sourceSkill -Recurse -File | ForEach-Object {
                        $skillRelative = $_.FullName.Substring($sourceSkill.Length + 1)
                        Add-FileFromSource -Source $_.FullName -Destination (Join-Path $ProjectRoot ".agents\skills\$skill\$skillRelative")
                    }
                }
            }
            'cursor' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\cursor\ai-spec.mdc.template') -Destination (Join-Path $ProjectRoot '.cursor\rules\ai-spec.mdc') -Variables $variables
            }
            'github-copilot' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\github-copilot\copilot-instructions.md.template') -Destination (Join-Path $ProjectRoot '.github\copilot-instructions.md') -Variables $variables
            }
            'generic' { }
        }
    }
}

function Add-ParentEntrypoints {
    param([string]$RootDir)

    $variables = @{
        'PARENT_NAME' = (Split-Path -Leaf $RootDir)
    }

    foreach ($tool in ($Tools | Select-Object -Unique)) {
        switch ($tool) {
            'claude-code' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\CLAUDE.md.template') -Destination (Join-Path $RootDir 'CLAUDE.md') -Variables $variables
            }
            'codex' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\AGENTS.md.template') -Destination (Join-Path $RootDir 'AGENTS.md') -Variables $variables
            }
            'cursor' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\ai-spec.mdc.template') -Destination (Join-Path $RootDir '.cursor\rules\ai-spec.mdc') -Variables $variables
            }
            'github-copilot' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\copilot-instructions.md.template') -Destination (Join-Path $RootDir '.github\copilot-instructions.md') -Variables $variables
            }
            'generic' {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\START-PROMPT.md.template') -Destination (Join-Path $RootDir 'START-PROMPT.md') -Variables $variables
            }
            default {
                Add-RenderedFile -Source (Join-Path $sourceRoot 'adapters\multi-project\START-PROMPT.md.template') -Destination (Join-Path $RootDir 'START-PROMPT.md') -Variables $variables
            }
        }
    }
}

function Get-ParentEntrypointPaths {
    param([string]$RootDir)

    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($tool in ($Tools | Select-Object -Unique)) {
        switch ($tool) {
            'claude-code' { $paths.Add((Join-Path $RootDir 'CLAUDE.md')) }
            'codex' { $paths.Add((Join-Path $RootDir 'AGENTS.md')) }
            'cursor' { $paths.Add((Join-Path $RootDir '.cursor\rules\ai-spec.mdc')) }
            'github-copilot' { $paths.Add((Join-Path $RootDir '.github\copilot-instructions.md')) }
            'generic' { $paths.Add((Join-Path $RootDir 'START-PROMPT.md')) }
            default { $paths.Add((Join-Path $RootDir 'START-PROMPT.md')) }
        }
    }
    return @($paths | Select-Object -Unique)
}

function Test-ParentEntrypointsReady {
    param([string]$RootDir)

    if (-not (Test-Path -LiteralPath (Join-Path $RootDir '.specforge.json') -PathType Leaf)) {
        return $false
    }

    foreach ($entryPath in Get-ParentEntrypointPaths -RootDir $RootDir) {
        if (-not (Test-Path -LiteralPath $entryPath -PathType Leaf)) {
            return $false
        }
        $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $entryPath
        if (-not ($content.Contains('.specforge.json') -and $content.Contains('.ai-spec/'))) {
            return $false
        }
    }

    return $true
}

function Test-ChildSpecsReady {
    param([hashtable[]]$InstallTargets)

    foreach ($target in $InstallTargets) {
        $projectRoot = [string]$target.path
        foreach ($relativePath in @('.ai-spec\AI-START.md', '.ai-spec\ai-spec.yaml', '.ai-spec\business\quick-ref.md')) {
            if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relativePath) -PathType Leaf)) {
                return $false
            }
        }
    }

    return $true
}

function Copy-RuntimeSpec {
    param([string]$SpecRoot)

    $runtimeFiles = @(
        'AI-START.md',
        'README.md',
        'ai-spec.example.yaml'
    )

    foreach ($relativePath in $runtimeFiles) {
        Add-FileFromSource -Source (Join-Path $sourceRoot $relativePath) -Destination (Join-Path $SpecRoot $relativePath)
    }

    $runtimeDirectories = @(
        'adapters', 'business', 'contracts', 'core', 'core-lite', 'governance',
        'scripts', 'skills', 'stacks', 'tests', 'workflows'
    )

    foreach ($directory in $runtimeDirectories) {
        $sourceDirectory = Join-Path $sourceRoot $directory
        Get-ChildItem -LiteralPath $sourceDirectory -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($sourceRoot.Length + 1)
            Add-FileFromSource -Source $_.FullName -Destination (Join-Path $SpecRoot $relativePath)
        }
    }

    $guide = Join-Path $sourceRoot 'docs\使用指南.md'
    if (Test-Path -LiteralPath $guide) {
        Add-FileFromSource -Source $guide -Destination (Join-Path $SpecRoot 'docs\使用指南.md')
    }
}

function Test-ProjectSignal {
    param(
        [string]$ProjectRoot,
        [string[]]$PathSignals,
        [string[]]$TextSignals
    )

    if (Test-PathAny -RootDir $ProjectRoot -RelativePaths $PathSignals) { return $true }

    $candidateFiles = @('package.json', 'requirements.txt', 'pyproject.toml', 'pom.xml', 'build.gradle', 'build.gradle.kts', 'go.mod')
    $text = ''
    foreach ($candidateFile in $candidateFiles) {
        $text += "`n" + (Read-FileIfExists -Path (Join-Path $ProjectRoot $candidateFile))
    }
    foreach ($signal in $TextSignals) {
        if ($text -match $signal) { return $true }
    }
    return $false
}

function Get-ProjectInventory {
    param(
        [string]$ProjectRoot,
        [bool]$IsMultiProject = $false
    )

    $ignoredDirs = @('.git', '.ai-spec', '.agents', '.claude', '.cursor', 'node_modules', 'vendor', 'dist', 'build', 'target', '.next', '.nuxt', 'coverage')
    $files = @(Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        $relative = $_.FullName.Substring($ProjectRoot.Length).TrimStart('\', '/')
        $parts = @($relative -split '[\\/]')
        $skip = $false
        foreach ($part in $parts) {
            if ($part -in $ignoredDirs) { $skip = $true; break }
        }
        -not $skip
    })

    $buildFiles = @('package.json', 'pom.xml', 'go.mod', 'Cargo.toml', 'requirements.txt', 'pyproject.toml', 'Makefile', 'build.gradle', 'build.gradle.kts', 'composer.json', 'mix.exs', 'CMakeLists.txt', 'BUILD', 'WORKSPACE')
    $buildFileCount = 0
    foreach ($buildFile in $buildFiles) {
        if (Test-Path -LiteralPath (Join-Path $ProjectRoot $buildFile) -PathType Leaf) { $buildFileCount++ }
    }

    $hasDatabase = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('prisma', 'migrations', 'db', 'database') -TextSignals @('prisma', 'typeorm', 'sequelize', 'sqlalchemy', 'hibernate', 'jdbc', 'postgres', 'mysql', 'sqlite', 'mongodb')
    $hasApi = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('api', 'routes', 'controllers', 'controller', 'server') -TextSignals @('api', 'route', 'controller', 'express', 'fastify', 'openapi', 'swagger')
    $hasAuth = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('auth', 'oauth', 'middleware', 'permission', 'permissions') -TextSignals @('auth', 'oauth', 'jwt', 'session', 'permission', 'tenant', 'rbac')
    $hasCi = Test-PathAny -RootDir $ProjectRoot -RelativePaths @('.github\workflows', '.gitlab-ci.yml', 'Jenkinsfile', 'azure-pipelines.yml', '.circleci', 'bitbucket-pipelines.yml')

    $fileCount = $files.Count
    $projectSize = 'enterprise'
    if ($fileCount -lt 30 -and $buildFileCount -le 1 -and -not $hasDatabase -and -not $hasApi -and -not $hasAuth -and -not $hasCi) {
        $projectSize = 'tiny'
    }
    elseif ($fileCount -lt 150) {
        $projectSize = 'small'
    }
    elseif ($fileCount -lt 800) {
        $projectSize = 'medium'
    }
    elseif ($fileCount -lt 3000) {
        $projectSize = 'large'
    }

    return @{
        fileCount = $fileCount
        buildFileCount = $buildFileCount
        hasDatabase = [bool]$hasDatabase
        hasApi = [bool]$hasApi
        hasAuth = [bool]$hasAuth
        hasCi = [bool]$hasCi
        multiProject = [bool]$IsMultiProject
        projectSize = $projectSize
    }
}

function Format-YamlInlineArray {
    param([string[]]$Items)

    $clean = @($Items | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    if ($clean.Count -eq 0) { return '[]' }
    return '[' + ($clean -join ', ') + ']'
}

function Get-PackageJsonObject {
    param([string]$ProjectRoot)

    $packagePath = Join-Path $ProjectRoot 'package.json'
    if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) { return $null }
    try {
        return (Get-Content -Raw -Encoding UTF8 -LiteralPath $packagePath | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Get-ProjectProfileInference {
    param([string]$ProjectRoot)

    $languages = [System.Collections.Generic.List[string]]::new()
    $frameworks = [System.Collections.Generic.List[string]]::new()
    $databases = [System.Collections.Generic.List[string]]::new()
    $packageManagers = [System.Collections.Generic.List[string]]::new()
    $commands = @{
        build = 'null'
        test = 'null'
        lint = 'null'
        typecheck = 'null'
        run = 'null'
    }

    $package = Get-PackageJsonObject -ProjectRoot $ProjectRoot
    if ($package) {
        $packageManagers.Add('npm')
        if (Test-Path -LiteralPath (Join-Path $ProjectRoot 'tsconfig.json')) { $languages.Add('typescript') }
        else { $languages.Add('javascript') }

        $dependencyText = (($package.dependencies | ConvertTo-Json -Depth 8 -Compress) + ' ' + ($package.devDependencies | ConvertTo-Json -Depth 8 -Compress)).ToLowerInvariant()
        foreach ($pair in @(
            @('react', 'react'),
            @('vue', 'vue'),
            @('next', 'nextjs'),
            @('@umijs/max', 'umi'),
            @('vite', 'vite'),
            @('express', 'express'),
            @('fastify', 'fastify'),
            @('antd', 'antd'),
            @('nestjs', 'nestjs')
        )) {
            if ($dependencyText.Contains($pair[0])) { $frameworks.Add($pair[1]) }
        }
        foreach ($pair in @(
            @('mysql', 'mysql'),
            @('pg', 'postgres'),
            @('postgres', 'postgres'),
            @('sqlite', 'sqlite'),
            @('mongodb', 'mongodb'),
            @('mongoose', 'mongodb'),
            @('redis', 'redis'),
            @('prisma', 'prisma')
        )) {
            if ($dependencyText.Contains($pair[0])) { $databases.Add($pair[1]) }
        }

        if ($package.scripts) {
            if ($package.scripts.PSObject.Properties.Name -contains 'build') { $commands.build = 'npm run build' }
            if ($package.scripts.PSObject.Properties.Name -contains 'test') { $commands.test = 'npm run test' }
            if ($package.scripts.PSObject.Properties.Name -contains 'lint') { $commands.lint = 'npm run lint' }
            if ($package.scripts.PSObject.Properties.Name -contains 'typecheck') { $commands.typecheck = 'npm run typecheck' }
            elseif ($package.scripts.PSObject.Properties.Name -contains 'tsc') { $commands.typecheck = 'npm run tsc' }
            if ($package.scripts.PSObject.Properties.Name -contains 'dev') { $commands.run = 'npm run dev' }
            elseif ($package.scripts.PSObject.Properties.Name -contains 'start') { $commands.run = 'npm start' }
        }
    }

    if (Test-Path -LiteralPath (Join-Path $ProjectRoot 'go.mod') -PathType Leaf) {
        $languages.Add('go')
        $packageManagers.Add('go')
        $goMod = Read-FileIfExists -Path (Join-Path $ProjectRoot 'go.mod')
        foreach ($pair in @(@('gin-gonic/gin', 'gin'), @('labstack/echo', 'echo'), @('gofiber/fiber', 'fiber'))) {
            if ($goMod.Contains($pair[0])) { $frameworks.Add($pair[1]) }
        }
        if ($commands.build -eq 'null') { $commands.build = 'go build ./...' }
        if ($commands.test -eq 'null') { $commands.test = 'go test ./...' }
        if ($commands.run -eq 'null') { $commands.run = 'go run .' }
    }

    if ((Test-Path -LiteralPath (Join-Path $ProjectRoot 'pom.xml') -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $ProjectRoot '.project') -PathType Leaf)) {
        $languages.Add('java')
        if (Test-Path -LiteralPath (Join-Path $ProjectRoot 'pom.xml') -PathType Leaf) {
            $packageManagers.Add('maven')
            $pom = Read-FileIfExists -Path (Join-Path $ProjectRoot 'pom.xml')
            if ($pom -match 'spring-boot|org\.springframework') { $frameworks.Add('spring') }
            if ($pom -match 'mysql') { $databases.Add('mysql') }
            if ($pom -match 'postgres') { $databases.Add('postgres') }
            if ($commands.build -eq 'null') { $commands.build = 'mvn package' }
            if ($commands.test -eq 'null') { $commands.test = 'mvn test' }
        }
    }

    if ((Test-Path -LiteralPath (Join-Path $ProjectRoot 'build.gradle') -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $ProjectRoot 'build.gradle.kts') -PathType Leaf)) {
        $languages.Add('java')
        $packageManagers.Add('gradle')
        if ($commands.build -eq 'null') { $commands.build = 'gradle build' }
        if ($commands.test -eq 'null') { $commands.test = 'gradle test' }
    }

    if ((Test-Path -LiteralPath (Join-Path $ProjectRoot 'requirements.txt') -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $ProjectRoot 'pyproject.toml') -PathType Leaf)) {
        $languages.Add('python')
        $packageManagers.Add('pip')
        $pythonText = (Read-FileIfExists -Path (Join-Path $ProjectRoot 'requirements.txt')) + "`n" + (Read-FileIfExists -Path (Join-Path $ProjectRoot 'pyproject.toml'))
        foreach ($pair in @(@('django', 'django'), @('fastapi', 'fastapi'), @('flask', 'flask'), @('pandas', 'pandas'))) {
            if ($pythonText -match $pair[0]) { $frameworks.Add($pair[1]) }
        }
        foreach ($pair in @(@('mysql', 'mysql'), @('psycopg|postgres', 'postgres'), @('sqlite', 'sqlite'), @('pymongo', 'mongodb'), @('redis', 'redis'))) {
            if ($pythonText -match $pair[0]) { $databases.Add($pair[1]) }
        }
        if ($commands.test -eq 'null') { $commands.test = 'pytest' }
        if ($commands.run -eq 'null') { $commands.run = 'python main.py' }
    }

    return @{
        languages = Format-YamlInlineArray -Items @($languages)
        frameworks = Format-YamlInlineArray -Items @($frameworks)
        databases = Format-YamlInlineArray -Items @($databases)
        packageManagers = Format-YamlInlineArray -Items @($packageManagers)
        commands = $commands
    }
}

function Get-SizeStrategy {
    param([string]$ProjectSize)

    switch ($ProjectSize) {
        'tiny' { return 'ultra-lite' }
        'small' { return 'lite' }
        'medium' { return 'focused' }
        'large' { return 'mapped' }
        'enterprise' { return 'governed' }
        default { return 'auto' }
    }
}

function Get-ProjectSignalMatrix {
    param([string]$ProjectRoot)

    return @{
        organization = (Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('auth', 'user', 'users', 'tenant', 'role', 'roles', 'account', 'accounts') -TextSignals @('auth', 'user', 'tenant', 'role', 'rbac', 'oauth', 'session', 'jwt'))
        kpi = (Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('reports', 'report', 'analytics', 'dashboard', 'metrics', 'kpi') -TextSignals @('kpi', 'metric', 'analytics', 'dashboard', 'report', '统计', '报表'))
        stateMachine = (Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('workflow', 'workflows', 'state', 'states', 'approval', 'task', 'order') -TextSignals @('status', 'state', 'workflow', 'approval', 'pending', 'completed', 'canceled'))
        permissionMenu = (Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('admin', 'menu', 'menus', 'permission', 'permissions', 'role', 'roles') -TextSignals @('permission', 'menu', 'admin', 'role', 'rbac', '权限', '菜单'))
        externalIntegration = (Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('webhook', 'webhooks', 'callback', 'callbacks', 'integrations', 'integration', 'third-party') -TextSignals @('webhook', 'callback', 'integration', 'third-party', 'oauth', 'api key', 'external'))
    }
}

function New-BusinessRulesSkeleton {
    param(
        [string]$ProjectRoot,
        [string]$ProjectType
    )

    $signals = Get-ProjectSignalMatrix -ProjectRoot $ProjectRoot
    $optionalSections = @(
        @{ id = 'organization-identity'; include = [bool]$signals.organization; reason = 'no organization/auth/user/tenant signal' },
        @{ id = 'kpi-metrics'; include = [bool]$signals.kpi; reason = 'no KPI/report/analytics signal' },
        @{ id = 'state-machines'; include = [bool]$signals.stateMachine; reason = 'no state/workflow/status signal' },
        @{ id = 'menu-permissions'; include = [bool]$signals.permissionMenu; reason = 'no admin/menu/permission signal' },
        @{ id = 'external-integrations'; include = [bool]$signals.externalIntegration; reason = 'no webhook/callback/integration signal' }
    )

    $omitted = @($optionalSections | Where-Object { -not $_.include })
    $omittedLines = if ($omitted.Count -gt 0) {
        ($omitted | ForEach-Object { "- $($_.id): $($_.reason)" }) -join "`n"
    }
    else {
        "- none"
    }

    $content = @"
# 业务规则

> SpecForge 接入生成的瘦身骨架。
> 本文件只记录业务语义，不记录技术栈、命令或临时聊天上下文。
> 填写真实规则时必须补充来源和可靠度标记。

metadata:
  projectType: $ProjectType
  generation: trimmed-skeleton
  omittedSections:
$omittedLines

---

<!-- section: business-positioning -->
## 业务定位

- 核心用户：待填充
- 核心价值：待填充
- 商业模式（如有）：待填充

<!-- section: business-domains -->
## 业务域

| 业务域 | 说明 | 能力 | 模块 |
|---|---|---|---|
| 待填充 |  |  |  |

"@

    foreach ($section in $optionalSections) {
        if (-not $section.include) { continue }
        switch ($section.id) {
            'organization-identity' {
                $content += @"

<!-- section: organization-identity -->
## 组织身份

- 身份来源：待填充
- 用户/租户/角色映射：待填充
- 数据范围规则：待填充

"@
            }
            'kpi-metrics' {
                $content += @"

<!-- section: kpi-metrics -->
## KPI 与指标

| 指标 | 时间范围 | 数据来源 | 排除规则 |
|---|---|---|---|
| 待填充 |  |  |  |

"@
            }
            'state-machines' {
                $content += @"

<!-- section: state-machines -->
## 状态机

- 实体：待填充
- 状态流转：待填充
- 触发条件和副作用：待填充

"@
            }
            'menu-permissions' {
                $content += @"

<!-- section: menu-permissions -->
## 菜单与权限

| 菜单 | 操作 | 权限码 | 角色 |
|---|---|---|---|
| 待填充 |  |  |  |

"@
            }
            'external-integrations' {
                $content += (@(
                    ''
                    '<!-- section: external-integrations -->'
                    '## 外部集成'
                    ''
                    '- 外部系统：待填充'
                    '- 数据流：待填充'
                    '- 鉴权、幂等、重试、审计：待填充'
                    ''
                ) -join "`n")
            }
        }
    }

    $content += @"

<!-- section: data-write-rules -->
## 数据写入规则

- 写操作必须幂等。
- 敏感变更必须可追踪。
- 不写死用户、员工、部门、角色、公司或租户 ID。
- 不用删除生产数据来“修复”业务问题。

<!-- section: business-invariants -->
## 业务不变量

- 待填充

<!-- section: uncategorized-business-rules -->
## 未归类业务规则

新规则应追加到匹配章节。若任务触发了已省略章节，先恢复对应章节。
"@

    return $content
}

function Write-BusinessRulesSkeleton {
    param(
        [string]$ProjectRoot,
        [string]$SpecRoot,
        [string]$ProjectType
    )

    $rulesPath = Join-Path $SpecRoot 'business\business-rules.md'
    if (-not (Test-Path -LiteralPath $rulesPath -PathType Leaf)) { return }

    $existing = Get-Content -Raw -Encoding UTF8 -LiteralPath $rulesPath
    if ($existing -match '(?m)^(?!\s*>).*\[📌 用户确认\]') {
        $script:conflicts.Add($rulesPath)
        return
    }

    $script:actions.Add("RENDER $rulesPath (trimmed business-rules skeleton)")
    if ($Apply) {
        $content = New-BusinessRulesSkeleton -ProjectRoot $ProjectRoot -ProjectType $ProjectType
        [System.IO.File]::WriteAllText($rulesPath, $content, [System.Text.UTF8Encoding]::new($false))
    }
}

function Write-QuickRefSkeleton {
    param(
        [string]$ProjectRoot,
        [string]$SpecRoot,
        [string]$ProjectType,
        [string]$ProjectSize,
        [string]$SizeStrategy
    )

    $quickRefPath = Join-Path $SpecRoot 'business\quick-ref.md'
    if (-not (Test-Path -LiteralPath $quickRefPath -PathType Leaf)) { return }

    $inventory = Get-ProjectInventory -ProjectRoot $ProjectRoot -IsMultiProject $false
    $maintenanceIntervalDays = switch ($ProjectSize) {
        { $_ -in @('tiny', 'small') } { 30; break }
        'medium' { 14; break }
        { $_ -in @('large', 'enterprise') } { 7; break }
        default { 14 }
    }
    $maintenanceDue = (Get-Date).Date.AddDays($maintenanceIntervalDays).ToString('yyyy-MM-dd')
    $script:actions.Add("RENDER $quickRefPath (project-size context strategy)")
    if ($Apply) {
    $content = @"
# 业务快速参考

> 日常启动唯一入口：普通会话只读本文件；maintenanceDue 到期才读 .ai-spec/workflows/context-maintenance.md；大文件先搜索并按不超过 250 行分段读取
> status: TEMPLATE_PLACEHOLDER
> dailyEntry: true
> dynamicContextGate: true
> outputLanguage: zh-CN
> maintenanceDue: $maintenanceDue
> projectSize: $ProjectSize
> sizeStrategy: $SizeStrategy
> 生成真实项目摘要后才能改为 GENERATED。
## 项目定位

- 项目类型/规模/策略：$ProjectType / $ProjectSize / $SizeStrategy
- 信号：files=$($inventory.fileCount), build=$($inventory.buildFileCount), api=$($inventory.hasApi.ToString().ToLowerInvariant()), db=$($inventory.hasDatabase.ToString().ToLowerInvariant()), auth=$($inventory.hasAuth.ToString().ToLowerInvariant()), ci=$($inventory.hasCi.ToString().ToLowerInvariant())

## 动态上下文门禁

| 等级 | 默认读取 | 升级条件 |
|---|---|---|
| L0 | 仅本文件 | 项目定位不清 |
| L1 | 本文件 + 精确命中文件片段 | 行为发生变化 |
| L2 | 本文件 + core-lite/delivery-lite.md + 相关源码 | 涉及测试或安全 |
| L3 | 命中的 business-rules/contracts/core 章节 | 公开契约、鉴权、迁移或敏感数据边界实际变化 |
| L4 | AI-START.md + 完整接入/审计上下文 | 用户要求接入、审计或重构 |

## 实施硬门禁（含计划自动触发门禁）

执行任何实施任务前自动判定，无需用户额外提醒。项目级/分阶段、多模块验收或跨 API/数据/鉴权/安全/进程边界时，读取 `.ai-spec/workflows/project-planning.md`。未落盘 `docs/plans/project-plan.md` 和 `docs/plans/current.md` 前不得改业务代码。

新增/调整模块、目录、共享抽象或跨模块调用时读 `.ai-spec/core/architecture.md`，检查 `docs/architecture/modules.md`；缺失则用 `.ai-spec/governance/module-contract-template.md` 建最小模块契约。

改 API/DTO/DB/权限/页面/进程/外部系统时填写影响矩阵；涉及核心链路时检查 `docs/quality/regression-checklist.md`，缺失则用 `.ai-spec/governance/regression-checklist-template.md` 建最小回归清单。

## 业务事实

- 待填充：AI 必须读取真实项目事实后再填写。
"@
        [System.IO.File]::WriteAllText($quickRefPath, $content, [System.Text.UTF8Encoding]::new($false))
    }
}

function Invoke-SpecSlimming {
    param(
        [string]$ProjectRoot,
        [string]$SpecRoot,
        [string]$ProjectType
    )

    Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'tests' -Reason 'template self-tests are not needed in installed projects'
    Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'scripts\install.ps1' -Reason 'one-time installer is not needed after onboarding'

    $adaptersRoot = Join-Path $SpecRoot 'adapters'
    if (Test-Path -LiteralPath $adaptersRoot -PathType Container) {
        Get-ChildItem -LiteralPath $adaptersRoot -Directory | ForEach-Object {
            if ($_.Name -notin $Tools) {
                Remove-SpecPath -SpecRoot $SpecRoot -RelativePath ("adapters\" + $_.Name) -Reason 'unused adapter'
            }
        }
    }

    $keepStacks = @(Get-StackFilesForType -ProjectType $ProjectType)
    $stacksRoot = Join-Path $SpecRoot 'stacks'
    if (Test-Path -LiteralPath $stacksRoot -PathType Container) {
        Get-ChildItem -LiteralPath $stacksRoot -File | ForEach-Object {
            if ($_.Name -notin $keepStacks) {
                Remove-SpecPath -SpecRoot $SpecRoot -RelativePath ("stacks\" + $_.Name) -Reason "irrelevant for $ProjectType project"
            }
        }
    }

    $hasDatabase = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('prisma', 'migrations', 'db', 'database') -TextSignals @('prisma', 'typeorm', 'sequelize', 'sqlalchemy', 'hibernate', 'jdbc', 'postgres', 'mysql', 'sqlite', 'mongodb')
    if (-not $hasDatabase) {
        Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'core\data-migration-standard.md' -Reason 'no database or migration signal detected'
    }

    $hasCi = Test-PathAny -RootDir $ProjectRoot -RelativePaths @('.github\workflows', '.gitlab-ci.yml', 'Jenkinsfile', 'azure-pipelines.yml', '.circleci', 'bitbucket-pipelines.yml')
    if (-not $hasCi) {
        Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'core\cicd-standard.md' -Reason 'no CI signal detected'
    }

    $hasPermission = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('auth', 'oauth', 'middleware') -TextSignals @('auth', 'oauth', 'jwt', 'session', 'permission', 'tenant', 'rbac')
    if (-not $hasPermission) {
        Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'core\permission-standard.md' -Reason 'no auth or permission signal detected'
    }

    $hasObservability = Test-ProjectSignal -ProjectRoot $ProjectRoot -PathSignals @('monitoring', 'observability', 'prometheus', 'grafana') -TextSignals @('sentry', 'prometheus', 'opentelemetry', 'datadog', 'newrelic', 'grafana')
    if (-not $hasObservability) {
        Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'core\observability.md' -Reason 'no observability signal detected'
    }

    Remove-SpecPath -SpecRoot $SpecRoot -RelativePath 'core\gotchas.md' -Reason 'no project-specific gotchas have been modeled yet'
}

function Test-ProjectPlanReady {
    param([string]$ProjectRoot)

    return (Test-Path -LiteralPath (Join-Path $ProjectRoot 'docs\plans\project-plan.md') -PathType Leaf)
}

function Install-SpecInstance {
    param(
        [string]$ProjectRoot,
        [string]$Stage,
        [string]$ProjectType,
        [string]$MultiProjectId
    )

    $specRoot = Join-Path $ProjectRoot '.ai-spec'
    $inventory = Get-ProjectInventory -ProjectRoot $ProjectRoot -IsMultiProject ([bool]$MultiProjectId)
    $sizeStrategy = Get-SizeStrategy -ProjectSize $inventory.projectSize
    Copy-RuntimeSpec -SpecRoot $specRoot
    Write-AiSpecProfile -SpecRoot $specRoot -ProjectRoot $ProjectRoot -Stage $Stage -ProjectType $ProjectType -MultiProjectId $MultiProjectId
    Add-AdapterEntrypoints -ProjectRoot $ProjectRoot
    if ($Onboard) {
        Write-QuickRefSkeleton -ProjectRoot $ProjectRoot -SpecRoot $specRoot -ProjectType $ProjectType -ProjectSize $inventory.projectSize -SizeStrategy $sizeStrategy
        Write-BusinessRulesSkeleton -ProjectRoot $ProjectRoot -SpecRoot $specRoot -ProjectType $ProjectType
        if ($Stage -eq 'new' -and -not (Test-ProjectPlanReady -ProjectRoot $ProjectRoot)) {
            $script:actions.Add("SKIP_SLIM $specRoot (new project requires docs\plans\project-plan.md first)")
        }
        else {
            Invoke-SpecSlimming -ProjectRoot $ProjectRoot -SpecRoot $specRoot -ProjectType $ProjectType
        }
    }

    $script:installReports.Add(@{
        path = $ProjectRoot
        stage = $Stage
        type = $ProjectType
    })
}

function Write-SpecForgeIndex {
    param(
        [string]$RootDir,
        [string]$MultiProjectId,
        [array]$Projects
    )

    $indexPath = Join-Path $RootDir '.specforge.json'
    if (Test-Path -LiteralPath $indexPath) {
        $script:conflicts.Add($indexPath)
        return
    }

    $script:actions.Add("CREATE $indexPath")
    if ($Apply) {
        $installedAt = (Get-Date).ToUniversalTime().ToString('o')
        $indexProjects = @()
        foreach ($project in $Projects) {
            $indexProjects += [ordered]@{
                path = $project.name
                type = $project.type
                buildFiles = @($project.buildFiles)
                installedAt = $installedAt
            }
        }
        $index = [ordered]@{
            templateSource = 'SpecForge'
            templateVersion = $templateVersion
            multiProjectId = $MultiProjectId
            projects = $indexProjects
        }
        $json = $index | ConvertTo-Json -Depth 6
        [System.IO.File]::WriteAllText($indexPath, $json, [System.Text.UTF8Encoding]::new($false))
    }
}

function Remove-ParentSpecInstance {
    param(
        [string]$RootDir,
        [hashtable[]]$InstallTargets
    )

    $rootFull = [System.IO.Path]::GetFullPath($RootDir).TrimEnd('\', '/')
    $parentSpecRoot = Join-Path $RootDir '.ai-spec'
    $parentSpecFull = [System.IO.Path]::GetFullPath($parentSpecRoot)
    $expectedSpecFull = [System.IO.Path]::GetFullPath((Join-Path $rootFull '.ai-spec'))

    if (-not $parentSpecFull.Equals($expectedSpecFull, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove unexpected parent spec path: $parentSpecFull"
    }

    if (Test-Path -LiteralPath $parentSpecFull -PathType Container) {
        if (-not (Test-ParentEntrypointsReady -RootDir $RootDir)) {
            $script:actions.Add("KEEP_PARENT_SPEC $parentSpecFull (parent lightweight entries are not fully configured yet)")
            return
        }
        if (-not (Test-ChildSpecsReady -InstallTargets $InstallTargets)) {
            $script:actions.Add("KEEP_PARENT_SPEC $parentSpecFull (child .ai-spec instances are not fully configured yet)")
            return
        }

        $script:actions.Add("REMOVE_PARENT_SPEC $parentSpecFull (child specs and parent lightweight entries are ready)")
        if ($Apply) {
            Remove-Item -LiteralPath $parentSpecFull -Recurse -Force
        }
    }
}

function Get-SyncRelativePaths {
    $relativePaths = [System.Collections.Generic.List[string]]::new()
    foreach ($file in @('AI-START.md', 'README.md', 'scripts\validate.ps1', 'scripts\git-preflight.ps1', 'scripts\update.ps1', 'scripts\update.cmd', 'scripts\update.sh', 'scripts\maintain-context.ps1', 'scripts\maintain-context.sh', 'scripts\audit-global-context.ps1')) {
        $relativePaths.Add($file)
    }

    foreach ($directory in @('core', 'core-lite', 'contracts', 'governance', 'skills', 'workflows')) {
        $sourceDirectory = Join-Path $sourceRoot $directory
        if (Test-Path -LiteralPath $sourceDirectory -PathType Container) {
            Get-ChildItem -LiteralPath $sourceDirectory -Recurse -File | ForEach-Object {
                $relativePaths.Add($_.FullName.Substring($sourceRoot.Length + 1))
            }
        }
    }

    return @($relativePaths | Select-Object -Unique)
}

function Copy-SyncFile {
    param(
        [string]$SpecRoot,
        [string]$RelativePath
    )

    $source = Join-Path $sourceRoot $RelativePath
    $destination = Join-Path $SpecRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        return
    }

    $script:actions.Add("SYNC $destination")
    if ($Apply) {
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

function Ensure-InstanceCompatibilityDefaults {
    param([string]$SpecRoot)

    $profilePath = Join-Path $SpecRoot 'ai-spec.yaml'
    if (Test-Path -LiteralPath $profilePath -PathType Leaf) {
        $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath
        $newline = if ($profile.Contains("`r`n")) { "`r`n" } else { "`n" }
        $updatedProfile = $profile

        if ($updatedProfile -notmatch '(?m)^  scope:\s*project-only\b') {
            $updatedProfile = [regex]::Replace($updatedProfile, '(?m)^spec:\s*$', "spec:${newline}  scope: project-only         # compatibility default; project scope only", 1)
        }
        if ($updatedProfile -notmatch '(?m)^  maintenance:\s*$') {
            $maintenanceBlock = @(
                '  maintenance:',
                '    enabled: true',
                '    strategy: lazy',
                '    autoApply: safe-only',
                '    intervalDaysBySize: { tiny: 30, small: 30, medium: 14, large: 7, enterprise: 7 }',
                '    quickRefMaxLines: 40',
                '    currentPlanMaxLines: 80',
                '    singleReadMaxLines: 250'
            ) -join $newline
            $updatedProfile = [regex]::Replace($updatedProfile, '(?m)^  projectSizeSignals:', ($maintenanceBlock + $newline + '  projectSizeSignals:'), 1)
        }
        if ($updatedProfile -notmatch '(?m)^  outputLanguage:\s*$') {
            $languageBlock = "  outputLanguage:${newline}    default: zh-CN${newline}    locked: true${newline}    overrideOnlyByExplicitUserRequest: true"
            $updatedProfile = [regex]::Replace($updatedProfile, '(?m)^(  specPath:.*)$', ('$1' + $newline + $languageBlock), 1)
        }
        elseif ($updatedProfile -notmatch '(?m)^    overrideOnlyByExplicitUserRequest:\s*true\s*$') {
            $updatedProfile = [regex]::Replace($updatedProfile, '(?m)^(    locked:\s*true.*)$', ('$1' + $newline + '    overrideOnlyByExplicitUserRequest: true'), 1)
        }
        if ($updatedProfile -notmatch '(?m)^  skillPolicy:\s*$') {
            $updatedProfile = $updatedProfile.TrimEnd() + $newline + "  skillPolicy:${newline}    mode: project-first${newline}    allowLocalSkills: true${newline}    reportSkillSource: true" + $newline
        }

        if ($updatedProfile -ne $profile) {
            $script:actions.Add("MIGRATE $profilePath (add missing project-only compatibility defaults)")
            if ($Apply) {
                [System.IO.File]::WriteAllText($profilePath, $updatedProfile, [System.Text.UTF8Encoding]::new($false))
            }
        }
    }

    $quickRefPath = Join-Path $SpecRoot 'business\quick-ref.md'
    if (Test-Path -LiteralPath $quickRefPath -PathType Leaf) {
        $quickRef = Get-Content -Raw -Encoding UTF8 -LiteralPath $quickRefPath
        $newline = if ($quickRef.Contains("`r`n")) { "`r`n" } else { "`n" }
        $updatedQuickRef = $quickRef
        if ($updatedQuickRef -notmatch '(?m)^>\s*outputLanguage:\s*zh-CN\s*$') {
            $updatedQuickRef = [regex]::Replace($updatedQuickRef, '(?m)^(>\s*dynamicContextGate:.*)$', ('$1' + $newline + '> outputLanguage: zh-CN'), 1)
        }
        if ($updatedQuickRef -notmatch '(?m)^>\s*maintenanceDue:\s*(auto|\d{4}-\d{2}-\d{2})\s*$') {
            $maintenanceDue = (Get-Date).Date.AddDays(14).ToString('yyyy-MM-dd')
            $updatedQuickRef = [regex]::Replace($updatedQuickRef, '(?m)^(>\s*outputLanguage:.*)$', ('$1' + $newline + "> maintenanceDue: $maintenanceDue"), 1)
        }

        $quickLines = [System.Collections.Generic.List[string]]::new()
        foreach ($line in @($updatedQuickRef -split '\r?\n')) { $quickLines.Add($line) }
        while ($quickLines.Count -gt 40) {
            $blankIndex = -1
            for ($i = $quickLines.Count - 1; $i -ge 0; $i--) {
                if ([string]::IsNullOrWhiteSpace($quickLines[$i])) { $blankIndex = $i; break }
            }
            if ($blankIndex -lt 0) { break }
            $quickLines.RemoveAt($blankIndex)
        }
        $updatedQuickRef = [string]::Join($newline, $quickLines).TrimEnd() + $newline

        if ($updatedQuickRef -ne $quickRef) {
            $script:actions.Add("MIGRATE $quickRefPath (add missing lightweight compatibility markers)")
            if ($Apply) {
                [System.IO.File]::WriteAllText($quickRefPath, $updatedQuickRef, [System.Text.UTF8Encoding]::new($false))
            }
        }
    }
}

function Sync-SpecInstance {
    param([string]$SpecRoot)

    if (-not (Test-Path -LiteralPath $SpecRoot -PathType Container)) {
        $script:conflicts.Add("Missing .ai-spec instance: $SpecRoot")
        return
    }

    foreach ($relativePath in Get-SyncRelativePaths) {
        Copy-SyncFile -SpecRoot $SpecRoot -RelativePath $relativePath
    }
    Ensure-InstanceCompatibilityDefaults -SpecRoot $SpecRoot
}

function Update-SpecForgeIndexVersion {
    param([string]$IndexPath)

    $script:actions.Add("UPDATE $IndexPath templateVersion=$templateVersion")
    if ($Apply) {
        $index = Get-Content -Raw -Encoding UTF8 -LiteralPath $IndexPath | ConvertFrom-Json
        if (-not ($index.PSObject.Properties.Name -contains 'templateSource')) {
            $index | Add-Member -NotePropertyName 'templateSource' -NotePropertyValue 'SpecForge'
        }
        else {
            $index.templateSource = 'SpecForge'
        }
        if (-not ($index.PSObject.Properties.Name -contains 'templateVersion')) {
            $index | Add-Member -NotePropertyName 'templateVersion' -NotePropertyValue $templateVersion
        }
        else {
            $index.templateVersion = $templateVersion
        }
        $json = $index | ConvertTo-Json -Depth 8
        [System.IO.File]::WriteAllText($IndexPath, $json, [System.Text.UTF8Encoding]::new($false))
    }
}

function Invoke-SpecSync {
    param([string]$RootDir)

    $indexPath = Join-Path $RootDir '.specforge.json'
    if (Test-Path -LiteralPath $indexPath -PathType Leaf) {
        Update-SpecForgeIndexVersion -IndexPath $indexPath
        Add-ParentEntrypoints -RootDir $RootDir
        $index = Get-Content -Raw -Encoding UTF8 -LiteralPath $indexPath | ConvertFrom-Json
        foreach ($project in @($index.projects)) {
            $projectRoot = Join-Path $RootDir ([string]$project.path)
            Sync-SpecInstance -SpecRoot (Join-Path $projectRoot '.ai-spec')
        }
        return
    }

    $singleSpecRoot = Join-Path $RootDir '.ai-spec'
    if (Test-Path -LiteralPath $singleSpecRoot -PathType Container) {
        Sync-SpecInstance -SpecRoot $singleSpecRoot
        return
    }

    throw 'Sync requires either a parent .specforge.json or a local .ai-spec directory.'
}

function Invoke-GitOnboarding {
    param([string]$RepositoryRoot)

    $hasGit = Test-Path -LiteralPath (Join-Path $RepositoryRoot '.git')
    if (-not $hasGit) {
        $script:actions.Add("GIT init/add/initial-commit $RepositoryRoot (controlled exception for no-Git onboarding)")
        if ($Apply) {
            & git -C $RepositoryRoot init | Out-Null
            & git -C $RepositoryRoot add -A | Out-Null
            & git -C $RepositoryRoot commit -m 'chore: initial commit' | Out-Null
        }
    }

    $script:actions.Add("GIT create branch $BranchName")
    if ($Apply) {
        $branchExists = $false
        & git -C $RepositoryRoot show-ref --verify --quiet "refs/heads/$BranchName"
        if ($LASTEXITCODE -eq 0) { $branchExists = $true }
        if ($branchExists) {
            throw "Git branch already exists: $BranchName"
        }
        & git -C $RepositoryRoot switch -c $BranchName | Out-Null
    }
}

function Get-GitOnboardingRoots {
    param(
        [string]$RootDir,
        [hashtable[]]$InstallTargets,
        [hashtable[]]$SubProjects
    )

    if (-not $ManageGit -or $GitScope -eq 'none') {
        return @()
    }

    if ($GitScope -eq 'parent') {
        return @($RootDir)
    }

    if ($GitScope -eq 'projects') {
        return @($InstallTargets | ForEach-Object { [string]$_.path } | Select-Object -Unique)
    }

    if ($SubProjects.Count -ge 2 -and (Test-ParentGitScopeSignal -RootDir $RootDir)) {
        return @($RootDir)
    }

    return @($InstallTargets | ForEach-Object { [string]$_.path } | Select-Object -Unique)
}

if ($Sync) {
    Invoke-SpecSync -RootDir $targetFullPath
    Write-Host "AI Spec sync plan" -ForegroundColor Cyan
    Write-Host "Target: $targetFullPath"
    Write-Host "TemplateVersion: $templateVersion"
    Write-Host "Apply: $([bool]$Apply)"
    foreach ($action in $actions) { Write-Host "- $action" }
    if ($conflicts.Count -gt 0) {
        Write-Host "Conflicts / warnings:" -ForegroundColor Yellow
        foreach ($conflict in $conflicts) { Write-Host "- $conflict" -ForegroundColor Yellow }
    }
    exit 0
}

$subProjects = if ($Onboard) { @(Detect-SubProjects -RootDir $targetFullPath) } else { @() }
$installTargets = [System.Collections.Generic.List[hashtable]]::new()
$multiProjectId = $null
$indexProjects = $null

if ($Onboard -and $subProjects.Count -ge 2) {
    $multiProjectId = [guid]::NewGuid().ToString()
    foreach ($project in $subProjects) {
        $projectType = Detect-ProjectType -ProjectRoot $project.path
        $project.type = $projectType
        $stage = if ($Mode -eq 'auto') { Detect-Mode -ProjectRoot $project.path } else { $Mode }
        $installTargets.Add(@{
            path = $project.path
            stage = $stage
            type = $projectType
            multiProjectId = $multiProjectId
        })
    }
    $indexProjects = $subProjects
}
elseif ($Onboard -and $subProjects.Count -eq 1 -and $Mode -eq 'auto') {
    $project = $subProjects[0]
    $projectType = Detect-ProjectType -ProjectRoot $project.path
    $installTargets.Add(@{
        path = $project.path
        stage = Detect-Mode -ProjectRoot $project.path
        type = $projectType
        multiProjectId = $null
    })
}
else {
    $projectType = if ($Onboard) { Detect-ProjectType -ProjectRoot $targetFullPath } else { 'generic' }
    $stage = if ($Mode -eq 'auto') { Detect-Mode -ProjectRoot $targetFullPath } else { $Mode }
    $installTargets.Add(@{
        path = $targetFullPath
        stage = $stage
        type = $projectType
        multiProjectId = $null
    })
}

if ($Onboard -and $ManageGit) {
    foreach ($repositoryRoot in Get-GitOnboardingRoots -RootDir $targetFullPath -InstallTargets @($installTargets.ToArray()) -SubProjects @($subProjects)) {
        Invoke-GitOnboarding -RepositoryRoot $repositoryRoot
    }
}

if ($null -ne $indexProjects) {
    Write-SpecForgeIndex -RootDir $targetFullPath -MultiProjectId $multiProjectId -Projects $indexProjects
    Add-ParentEntrypoints -RootDir $targetFullPath
}

foreach ($target in $installTargets) {
    Install-SpecInstance -ProjectRoot $target.path -Stage $target.stage -ProjectType $target.type -MultiProjectId $target.multiProjectId
}

if ($null -ne $indexProjects) {
    Remove-ParentSpecInstance -RootDir $targetFullPath -InstallTargets @($installTargets.ToArray())
}

Write-Host "AI Spec installation plan" -ForegroundColor Cyan
Write-Host "Target: $targetFullPath"
Write-Host "Mode: $Mode"
Write-Host "Onboard: $([bool]$Onboard)"
Write-Host "ManageGit: $([bool]$ManageGit)"
Write-Host "GitScope: $GitScope"
Write-Host "Tools: $($Tools -join ', ')"
Write-Host "Apply: $([bool]$Apply)"
Write-Host "Instances: $($installReports.Count)"
foreach ($report in $installReports) {
    Write-Host "- $($report.path) [$($report.stage) / $($report.type)]"
}
Write-Host "Actions: $($actions.Count)"
foreach ($action in $actions) { Write-Host "- $action" }

if ($Onboard -and $Tools -contains 'claude-code') {
    $globalAuditScript = Join-Path $sourceRoot 'scripts\audit-global-context.ps1'
    if (Test-Path -LiteralPath $globalAuditScript -PathType Leaf) {
        & $globalAuditScript
    }
}

if ($conflicts.Count -gt 0) {
    Write-Host "Existing files kept unchanged: $($conflicts.Count)" -ForegroundColor Yellow
    foreach ($conflict in $conflicts) { Write-Host "- KEEP $conflict" }
    Write-Host 'Review and merge these files semantically; the installer never overwrites them.' -ForegroundColor Yellow
}

if (-not $Apply) {
    Write-Host 'Dry-run only. Re-run with -Apply to create missing files.' -ForegroundColor Yellow
}
elseif ($Onboard) {
    Write-Host 'Onboarding completed without overwriting existing user-owned files.' -ForegroundColor Green
}
else {
    Write-Host 'Installation completed without overwriting existing files.' -ForegroundColor Green
}

