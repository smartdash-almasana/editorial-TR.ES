"""Editorial TR.ES — HTML template de la consola web.

Implementación fiel del diseño "Mesa editorial" (sidebar literario argentino,
paleta cálida ámbar/tierra, tono voseo, cita en el footer del sidebar).

El archivo expone una sola variable INDEX_HTML con todo el CSS y JS inline,
consumiendo la API REST de app.py.
"""

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Editorial TR.ES · Mesa editorial</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
:root {
    --bg-canvas: #fafaf9;
    --bg-surface: #ffffff;
    --bg-muted: #f5f5f4;
    --bg-accent: #fef3c7;
    --text-primary: #1c1917;
    --text-secondary: #57534e;
    --text-tertiary: #a8a29e;
    --text-inverse: #ffffff;
    --border-subtle: #e7e5e4;
    --border-strong: #d6d3d1;
    --accent-primary: #b45309;
    --accent-primary-hover: #92400e;
    --accent-secondary: #1e40af;
    --accent-success: #059669;
    --accent-success-light: #d1fae5;
    --accent-warning: #d97706;
    --accent-danger: #dc2626;
    --accent-danger-light: #fee2e2;
    --accent-info: #0891b2;
    --accent-info-light: #cffafe;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.03);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.03);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.06), 0 4px 6px -4px rgb(0 0 0 / 0.03);
    --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.08), 0 8px 10px -6px rgb(0 0 0 / 0.05);
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 20px;
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-serif: 'Playfair Display', Georgia, serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    font-family: var(--font-sans); background: var(--bg-canvas);
    color: var(--text-primary); line-height: 1.6;
    -webkit-font-smoothing: antialiased; min-height: 100vh;
}
h1,h2,h3,h4 { font-weight: 600; line-height: 1.3; letter-spacing: -0.02em; color: var(--text-primary); }
h1 { font-size: 2.25rem; font-weight: 700; }
h2 { font-size: 1.625rem; }
h3 { font-size: 1.25rem; }
p { color: var(--text-secondary); }
a { color: inherit; }

/* ===== Layout ===== */
.app-layout { display: flex; min-height: 100vh; }
.app-sidebar {
    width: 260px; background: var(--bg-surface); border-right: 1px solid var(--border-subtle);
    padding: 24px 0; position: sticky; top: 0; height: 100vh; overflow-y: auto;
    display: flex; flex-direction: column;
}
.sidebar-brand { padding: 0 24px 24px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 16px; }
.brand-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.brand-logo {
    width: 36px; height: 36px; border-radius: 8px; background: var(--accent-primary);
    color: white; font-weight: 800; font-size: 14px; display: flex;
    align-items: center; justify-content: center; letter-spacing: -0.02em;
}
.brand-text { font-size: 1rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.brand-sub { font-size: 0.8125rem; color: var(--text-tertiary); font-weight: 500; padding-left: 48px; }
.sidebar-menu { list-style: none; padding: 0 12px; flex: 1; }
.sidebar-menu li { margin-bottom: 2px; }
.sidebar-menu a {
    display: flex; align-items: center; gap: 12px; padding: 10px 12px;
    border-radius: var(--radius-md); color: var(--text-secondary);
    text-decoration: none; font-size: 0.9375rem; font-weight: 500;
    transition: all var(--transition-fast); cursor: pointer;
}
.sidebar-menu a:hover { background: var(--bg-muted); color: var(--text-primary); }
.sidebar-menu a.active { background: var(--accent-primary); color: var(--text-inverse); font-weight: 600; }
.sidebar-menu a.active:hover { background: var(--accent-primary-hover); }
.sidebar-menu a svg { width: 18px; height: 18px; flex-shrink: 0; }
.sidebar-footer {
    padding: 20px 24px; border-top: 1px solid var(--border-subtle); margin-top: 16px;
}
.sidebar-footer-quote {
    font-family: var(--font-serif); font-style: italic; font-size: 0.875rem;
    color: var(--text-tertiary); line-height: 1.6;
}

/* ===== Top bar ===== */
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 40px; background: var(--bg-surface);
    border-bottom: 1px solid var(--border-subtle);
    position: sticky; top: 0; z-index: 50;
}
.top-bar-left { display: flex; align-items: center; gap: 12px; font-size: 0.9375rem; font-weight: 500; }
.top-bar-left .chip {
    padding: 4px 10px; border: 1px solid var(--border-strong);
    border-radius: 999px; font-size: 0.75rem; color: var(--text-secondary);
}
.top-bar-status {
    display: flex; align-items: center; gap: 8px; font-size: 0.8125rem;
    color: var(--accent-success); font-weight: 500;
}
.top-bar-status::before {
    content: ''; width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent-success);
}
.top-bar-avatar {
    width: 36px; height: 36px; border-radius: 50%; background: var(--bg-accent);
    color: var(--accent-primary); font-weight: 700; display: flex;
    align-items: center; justify-content: center; font-size: 0.8125rem;
    border: 1px solid var(--border-subtle);
}

/* ===== Main content ===== */
.main-content { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.view { padding: 40px; display: none; animation: fadeIn var(--transition-base); }
.view.active { display: block; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

/* ===== Hero ===== */
.hero {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl); padding: 48px; margin-bottom: 32px;
    display: grid; grid-template-columns: 1fr auto; gap: 40px; align-items: center;
}
.hero-tag {
    display: inline-block; font-size: 0.75rem; font-weight: 600;
    color: var(--accent-primary); text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 12px;
}
.hero h1 { margin-bottom: 12px; }
.hero h1 em { font-family: var(--font-serif); font-style: italic; font-weight: 400; color: var(--accent-primary); }
.hero p { font-size: 1.0625rem; max-width: 560px; margin-bottom: 24px; }
.hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.hero-aside {
    text-align: right; font-family: var(--font-serif); font-style: italic;
    color: var(--text-tertiary); font-size: 0.9375rem; max-width: 260px;
}

/* ===== Buttons ===== */
.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 11px 20px; border-radius: var(--radius-md); font-size: 0.875rem;
    font-weight: 600; text-decoration: none; border: 1px solid transparent;
    cursor: pointer; transition: all var(--transition-fast); font-family: inherit;
    line-height: 1;
}
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-primary { background: var(--accent-primary); color: white; }
.btn-primary:hover:not(:disabled) { background: var(--accent-primary-hover); transform: translateY(-1px); box-shadow: var(--shadow-md); }
.btn-primary:active:not(:disabled) { transform: translateY(0); }
.btn-secondary { background: var(--bg-surface); color: var(--text-primary); border-color: var(--border-strong); }
.btn-secondary:hover:not(:disabled) { background: var(--bg-muted); border-color: var(--text-tertiary); }
.btn-ghost { background: transparent; color: var(--text-secondary); }
.btn-ghost:hover:not(:disabled) { background: var(--bg-muted); color: var(--text-primary); }
.btn-success { background: var(--accent-success); color: white; }
.btn-success:hover:not(:disabled) { background: #047857; transform: translateY(-1px); box-shadow: var(--shadow-md); }
.btn-danger { background: var(--accent-danger); color: white; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; transform: translateY(-1px); box-shadow: var(--shadow-md); }
.btn-sm { padding: 7px 14px; font-size: 0.8125rem; }
.btn-lg { padding: 14px 26px; font-size: 0.9375rem; }

/* ===== Stats ===== */
.stats-row {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px;
}
.stat-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 20px 24px;
    transition: all var(--transition-base);
}
.stat-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.stat-number { font-size: 2rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.03em; line-height: 1; }
.stat-label { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); margin-top: 8px; }
.stat-sub { font-size: 0.8125rem; color: var(--text-tertiary); margin-top: 2px; }

/* ===== Section header ===== */
.section-head {
    display: flex; align-items: flex-end; justify-content: space-between;
    margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-subtle);
}
.section-head h2 { margin-bottom: 4px; }
.section-head p { font-size: 0.9375rem; }

/* ===== Works grid ===== */
.works-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
.work-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 24px;
    transition: all var(--transition-base); position: relative; overflow: hidden;
}
.work-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.work-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.work-card h3 { font-size: 1.125rem; margin-bottom: 8px; }
.work-card p { font-size: 0.875rem; min-height: 40px; }
.work-card-footer { margin-top: 20px; display: flex; align-items: center; justify-content: space-between; }
.badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
    border-radius: 999px; font-size: 0.6875rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
}
.badge-borrador { background: var(--bg-muted); color: var(--text-secondary); }
.badge-revisado, .badge-leida { background: var(--accent-info-light); color: var(--accent-info); }
.badge-aprobado, .badge-aprobada { background: var(--accent-success-light); color: var(--accent-success); }
.badge-exportado, .badge-exportada { background: var(--bg-accent); color: var(--accent-primary); }
.badge-missing { background: var(--accent-danger-light); color: var(--accent-danger); }

/* ===== Forms ===== */
.form-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl); padding: 40px; max-width: 760px;
}
.form-group { margin-bottom: 20px; }
.form-label {
    display: block; font-size: 0.8125rem; font-weight: 600;
    color: var(--text-primary); margin-bottom: 8px;
}
.form-input, .form-select, .form-textarea {
    width: 100%; padding: 11px 14px; border: 1px solid var(--border-strong);
    border-radius: var(--radius-md); font-size: 0.9375rem;
    font-family: inherit; background: var(--bg-surface); color: var(--text-primary);
    transition: all var(--transition-fast);
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
    outline: none; border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px rgb(180 83 9 / 0.12);
}
.form-textarea { resize: vertical; min-height: 80px; line-height: 1.5; }
.form-hint { font-size: 0.75rem; color: var(--text-tertiary); margin-top: 6px; }
.dropzone {
    border: 2px dashed var(--border-strong); border-radius: var(--radius-lg);
    padding: 40px 24px; text-align: center; background: var(--bg-muted);
    transition: all var(--transition-base); cursor: pointer; margin-top: 32px;
}
.dropzone:hover, .dropzone.drag {
    border-color: var(--accent-primary); background: var(--bg-accent);
}
.dropzone-icon {
    width: 48px; height: 48px; border-radius: 50%; background: var(--bg-surface);
    border: 1px solid var(--border-subtle); display: flex;
    align-items: center; justify-content: center; margin: 0 auto 16px;
}
.dropzone h3 { font-size: 1rem; margin-bottom: 4px; }
.dropzone p { font-size: 0.8125rem; }
.dropzone-file {
    display: none; margin-top: 16px; padding: 12px 16px; background: var(--bg-surface);
    border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
    font-size: 0.875rem;
}
.dropzone-file.visible { display: flex; align-items: center; justify-content: space-between; }

/* ===== Progress steps ===== */
.progress-steps {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px;
}
.step {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 16px 18px;
    display: flex; align-items: flex-start; gap: 12px;
    transition: all var(--transition-base);
}
.step-icon {
    width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8125rem; font-weight: 700; background: var(--bg-muted); color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
}
.step.done .step-icon { background: var(--accent-success-light); color: var(--accent-success); border-color: transparent; }
.step.active .step-icon { background: var(--accent-primary); color: white; border-color: transparent; }
.step-pending .step-icon { background: var(--bg-muted); color: var(--text-tertiary); }
.step-label { font-size: 0.8125rem; font-weight: 600; color: var(--text-primary); }
.step-sub { font-size: 0.75rem; color: var(--text-tertiary); margin-top: 2px; }

/* ===== Info grid ===== */
.info-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 20px 24px; margin-bottom: 28px;
}
.info-item-label { font-size: 0.75rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.info-item-value { font-size: 0.9375rem; color: var(--text-primary); font-weight: 600; margin-top: 4px; }

/* ===== Talleres ===== */
.talleres-intro {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl); padding: 40px; margin-bottom: 24px;
}
.talleres-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }
.taller-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 28px;
    transition: all var(--transition-base); position: relative;
}
.taller-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.taller-number {
    font-family: var(--font-serif); font-size: 2rem; font-weight: 600;
    color: var(--accent-primary); line-height: 1; margin-bottom: 14px;
}
.taller-status {
    position: absolute; top: 24px; right: 24px;
    padding: 3px 10px; border-radius: 999px; font-size: 0.6875rem;
    background: var(--accent-success-light); color: var(--accent-success);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
}
.taller-card h3 { font-size: 1.0625rem; margin-bottom: 10px; padding-right: 80px; }
.taller-card p { font-size: 0.875rem; margin-bottom: 20px; }
.taller-footer { display: flex; align-items: center; justify-content: space-between; }

/* ===== Findings ===== */
.finding-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg); padding: 28px; margin-bottom: 20px;
}
.finding-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-subtle);
}
.finding-type {
    display: flex; align-items: center; gap: 12px;
}
.finding-type-name { font-weight: 600; color: var(--text-primary); }
.finding-id {
    font-size: 0.75rem; color: var(--text-tertiary); font-family: 'SF Mono', Menlo, monospace;
    background: var(--bg-muted); padding: 2px 8px; border-radius: 4px;
}
.text-block {
    padding: 14px 18px; border-radius: var(--radius-md);
    font-size: 0.9375rem; line-height: 1.6; margin-bottom: 12px;
    font-family: Georgia, serif;
}
.text-block-label {
    display: block; font-size: 0.6875rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin-bottom: 6px; font-family: var(--font-sans);
}
.text-block.original { background: var(--accent-danger-light); border-left: 3px solid var(--accent-danger); }
.text-block.original .text-block-label { color: var(--accent-danger); }
.text-block.proposal { background: var(--accent-success-light); border-left: 3px solid var(--accent-success); }
.text-block.proposal .text-block-label { color: var(--accent-success); }
.finding-rationale {
    font-size: 0.875rem; color: var(--text-secondary);
    font-style: italic; margin: 16px 0;
}
.finding-actions { display: flex; gap: 10px; margin-top: 20px; }

/* ===== Downloads ===== */
.downloads-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.download-card {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl); padding: 32px; text-align: center;
    transition: all var(--transition-base);
}
.download-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-lg); transform: translateY(-3px); }
.download-icon {
    width: 72px; height: 72px; border-radius: 16px; margin: 0 auto 20px;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-serif); font-size: 2rem; font-weight: 600;
}
.download-icon.pdf { background: var(--bg-accent); color: var(--accent-primary); }
.download-icon.html { background: var(--accent-info-light); color: var(--accent-info); }
.download-icon.appbook { background: var(--accent-success-light); color: var(--accent-success); }
.download-card h3 { margin-bottom: 8px; }
.download-card p { font-size: 0.875rem; margin-bottom: 24px; min-height: 42px; }

/* ===== Toast ===== */
.toast-container { position: fixed; top: 24px; right: 24px; z-index: 1000; display: flex; flex-direction: column; gap: 10px; }
.toast {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md); padding: 14px 18px;
    box-shadow: var(--shadow-xl); min-width: 300px; max-width: 420px;
    display: flex; align-items: flex-start; gap: 12px;
    animation: slideIn var(--transition-base);
}
@keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.toast.success { border-left: 3px solid var(--accent-success); }
.toast.error { border-left: 3px solid var(--accent-danger); }
.toast.info { border-left: 3px solid var(--accent-info); }
.toast-icon { font-size: 1.125rem; }
.toast-body { flex: 1; }
.toast-title { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.toast-message { font-size: 0.8125rem; color: var(--text-secondary); }

/* ===== Modal ===== */
.modal-backdrop {
    position: fixed; inset: 0; background: rgba(28, 25, 23, 0.5); backdrop-filter: blur(4px);
    display: none; align-items: center; justify-content: center; z-index: 1000;
    animation: fadeIn var(--transition-base);
}
.modal-backdrop.active { display: flex; }
.modal {
    background: var(--bg-surface); border-radius: var(--radius-xl);
    padding: 40px; max-width: 520px; width: 90%;
    box-shadow: var(--shadow-xl); animation: fadeIn var(--transition-base);
}
.modal h2 { margin-bottom: 8px; }
.modal > p { margin-bottom: 24px; }
.modal-details {
    background: var(--bg-muted); border-radius: var(--radius-md);
    padding: 16px 20px; margin-bottom: 24px; font-size: 0.875rem;
}
.modal-details-row { display: flex; justify-content: space-between; padding: 6px 0; }
.modal-details-label { color: var(--text-tertiary); font-size: 0.8125rem; }
.modal-details-value { color: var(--text-primary); font-weight: 600; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }

/* ===== Spinner ===== */
.spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
    border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Empty state ===== */
.empty {
    text-align: center; padding: 60px 24px;
    background: var(--bg-surface); border: 1px dashed var(--border-strong);
    border-radius: var(--radius-lg);
}
.empty h3 { margin-bottom: 8px; }
.empty p { font-size: 0.875rem; }

/* ===== Responsive ===== */
@media (max-width: 900px) {
    .app-sidebar { display: none; }
    .top-bar, .view { padding-left: 20px; padding-right: 20px; }
    .hero { grid-template-columns: 1fr; padding: 32px 24px; }
    .stats-row, .progress-steps, .info-grid, .downloads-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="app-layout">

    <!-- ===== Sidebar ===== -->
    <aside class="app-sidebar">
        <div class="sidebar-brand">
            <div class="brand-row">
                <div class="brand-logo">TR</div>
                <div class="brand-text">Editorial TR.ES</div>
            </div>
            <div class="brand-sub">Mesa editorial</div>
        </div>
        <ul class="sidebar-menu" id="sidebar-menu">
            <li><a data-view="mesa" class="active">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                La mesa
            </a></li>
            <li><a data-view="nueva">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4"/></svg>
                Nueva obra
            </a></li>
            <li><a data-view="obra">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
                Obra abierta
            </a></li>
            <li><a data-view="talleres">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
                Talleres editoriales
            </a></li>
            <li><a data-view="observaciones">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
                Observaciones
            </a></li>
            <li><a data-view="ediciones">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Ediciones listas
            </a></li>
        </ul>
        <div class="sidebar-footer">
            <div class="sidebar-footer-quote">
                “Editar es escuchar lo que el texto todavía intenta decir.”
            </div>
        </div>
    </aside>

    <!-- ===== Main ===== -->
    <div class="main-content">
        <div class="top-bar">
            <div class="top-bar-left">
                <strong>Editorial TR.ES</strong>
                <span class="chip" id="topbar-menu-chip">Menú</span>
            </div>
            <div class="top-bar-status" id="topbar-status">Todo está en orden</div>
            <div class="top-bar-avatar">ET</div>
        </div>

        <!-- VIEW: La mesa -->
        <section class="view active" id="view-mesa">
            <div class="hero">
                <div>
                    <span class="hero-tag">Taller privado de edición</span>
                    <h1>Cada manuscrito merece una lectura <em>atenta</em>.</h1>
                    <p>Reuní en un solo lugar la obra, las observaciones, las decisiones editoriales y sus distintas ediciones, sin perder la voz de quien escribió.</p>
                    <div class="hero-actions">
                        <button class="btn btn-primary btn-lg" onclick="go('nueva')">Comenzar una obra</button>
                        <button class="btn btn-secondary btn-lg" onclick="loadWorks()">Volver al manuscrito</button>
                    </div>
                </div>
                <div class="hero-aside">
                    “La mesa editorial sostiene el diálogo entre la obra y sus decisiones.”
                </div>
            </div>

            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-number" id="stat-works">—</div>
                    <div class="stat-label">Obras en la mesa</div>
                    <div class="stat-sub" id="stat-works-sub">cargando…</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="stat-findings">—</div>
                    <div class="stat-label">Observaciones pendientes</div>
                    <div class="stat-sub">esperan una decisión</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="stat-exports">—</div>
                    <div class="stat-label">Ediciones terminadas</div>
                    <div class="stat-sub">listas para compartir</div>
                </div>
            </div>

            <div class="section-head">
                <div>
                    <h2>Obras recientes</h2>
                    <p>El estado de cada manuscrito y el próximo gesto editorial.</p>
                </div>
                <button class="btn btn-secondary" onclick="go('nueva')">Añadir una obra</button>
            </div>
            <div class="works-grid" id="works-grid">
                <div class="empty"><p>Cargando obras…</p></div>
            </div>
        </section>

        <!-- VIEW: Nueva obra -->
        <section class="view" id="view-nueva">
            <div class="hero">
                <div>
                    <span class="hero-tag">Nueva obra</span>
                    <h1>Abrí un lugar para el <em>manuscrito</em>.</h1>
                    <p>Ingresá sus datos esenciales y acercá el texto original.</p>
                </div>
            </div>

            <div class="form-card">
                <form id="new-work-form">
                    <div class="form-group">
                        <label class="form-label" for="f-title">Título de la obra</label>
                        <input class="form-input" type="text" id="f-title" required placeholder="El puerto y el río">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="f-author">Nombre de quien escribió</label>
                        <input class="form-input" type="text" id="f-author" placeholder="Opcional">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="f-language">Lengua de la obra</label>
                        <select class="form-select" id="f-language">
                            <option value="es">Español</option>
                            <option value="en">Inglés</option>
                            <option value="pt">Portugués</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="f-note">Una breve nota sobre la obra</label>
                        <textarea class="form-textarea" id="f-note" placeholder="Opcional"></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg" id="btn-create">
                        <span id="btn-create-label">Crear la obra</span>
                        <span id="btn-create-spinner" class="spinner" style="display:none"></span>
                    </button>
                </form>

                <div class="dropzone" id="dropzone">
                    <div class="dropzone-icon">
                        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <h3>Acercá el manuscrito</h3>
                    <p>Arrastrá aquí el archivo de texto o elegilo desde tu equipo.</p>
                    <input type="file" id="f-file" accept=".txt,.md,.text" style="display:none">
                    <div style="margin-top:14px">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="document.getElementById('f-file').click()">Elegir archivo</button>
                    </div>
                    <div class="dropzone-file" id="dropzone-file">
                        <span id="dropzone-file-name"></span>
                        <button type="button" class="btn btn-ghost btn-sm" onclick="clearFile()">✕</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- VIEW: Obra abierta -->
        <section class="view" id="view-obra">
            <div id="obra-empty" class="empty">
                <h3>No hay una obra abierta</h3>
                <p>Elegí una obra en <em>La mesa</em> para ver su detalle.</p>
            </div>
            <div id="obra-content" style="display:none">
                <div class="hero">
                    <div>
                        <span class="hero-tag">Obra abierta</span>
                        <h1 id="obra-title"></h1>
                        <p id="obra-status-text"></p>
                    </div>
                    <div class="hero-aside">
                        <span class="badge" id="obra-badge"></span>
                    </div>
                </div>

                <div class="progress-steps" id="obra-steps"></div>

                <div class="info-grid">
                    <div><div class="info-item-label">Original conservado</div><div class="info-item-value" id="obra-orig">Sí</div></div>
                    <div><div class="info-item-label">Partes reconocidas</div><div class="info-item-value" id="obra-parts">—</div></div>
                    <div><div class="info-item-label">Lengua</div><div class="info-item-value" id="obra-lang">—</div></div>
                </div>

                <div class="section-head">
                    <div>
                        <h2>Próximos gestos</h2>
                        <p>Continuá la edición con pasos claros y sin salir de la obra.</p>
                    </div>
                    <div style="font-size:0.8125rem;color:var(--text-tertiary)">
                        <span>Situación · <strong id="obra-situacion" style="color:var(--text-primary)">—</strong></span>
                        &nbsp;·&nbsp;
                        <span>Edición · <strong id="obra-edition" style="color:var(--text-primary)">Primera</strong></span>
                    </div>
                </div>

                <div style="display:flex; gap:12px; flex-wrap:wrap">
                    <button class="btn btn-secondary" onclick="runReview()" id="btn-review">Leer nuevamente</button>
                    <button class="btn btn-secondary" onclick="go('observaciones')" id="btn-findings">Ver observaciones</button>
                    <button class="btn btn-success" onclick="approveEdition()" id="btn-approve">Aprobar la edición</button>
                </div>
            </div>
        </section>

        <!-- VIEW: Talleres editoriales -->
        <section class="view" id="view-talleres">
            <div class="talleres-intro">
                <span class="hero-tag">Talleres editoriales</span>
                <h1 style="margin-bottom:10px">Cada lectura cumple una tarea <em>distinta</em>.</h1>
                <p>Aplicá sólo los procesos que la obra necesita y conservá siempre la voz original.</p>
            </div>

            <div class="talleres-grid">
                <div class="taller-card">
                    <div class="taller-number">01</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Corrección literaria</h3>
                    <p>Trabaja ritmo, claridad, repeticiones, tono, imágenes y fluidez sin uniformar la escritura. Busca mejorar la experiencia de lectura sin reemplazar la intención de quien escribió.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="toast('info','Taller','Abrí una obra y ejecutá la revisión.')">Iniciar lectura</button>
                    </div>
                </div>
                <div class="taller-card">
                    <div class="taller-number">02</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Corrección gramatical y ortográfica</h3>
                    <p>Revisa ortografía, puntuación, concordancias, tiempos verbales y construcción de las frases. Cada cambio queda presentado como observación para ser aceptado o descartado.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="toast('info','Taller','Abrí una obra y ejecutá la revisión.')">Revisar el texto</button>
                    </div>
                </div>
                <div class="taller-card">
                    <div class="taller-number">03</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Lectura de la voz autoral</h3>
                    <p>Reconoce vocabulario, cadencia, tono, punto de vista, recursos frecuentes y rasgos propios de la escritura. Sirve como resguardo para que futuras correcciones no borren la identidad de la obra.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="toast('info','Taller','Función disponible próximamente.')">Reconocer la voz</button>
                    </div>
                </div>
                <div class="taller-card">
                    <div class="taller-number">04</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Análisis de la estructura</h3>
                    <p>Observa capítulos, escenas, progresión, vacíos, repeticiones, orden interno y equilibrio entre las partes. Permite ver la arquitectura completa antes de intervenir sobre los fragmentos.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="toast('info','Taller','Función disponible próximamente.')">Examinar la estructura</button>
                    </div>
                </div>
                <div class="taller-card">
                    <div class="taller-number">05</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Unir varios archivos</h3>
                    <p>Ordena capítulos, notas y fragmentos dispersos para formar un único manuscrito continuo. Respeta el orden elegido, identifica títulos repetidos y señala partes faltantes.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="toast('info','Taller','Función disponible próximamente.')">Elegir archivos</button>
                    </div>
                </div>
                <div class="taller-card">
                    <div class="taller-number">06</div>
                    <div class="taller-status">Disponible</div>
                    <h3>Preparar otras ediciones</h3>
                    <p>Convierte la obra terminada en distintos formatos para impresión, pantalla, distribución y lectura interactiva. Una misma edición maestra alimenta todas las versiones.</p>
                    <div class="taller-footer">
                        <button class="btn btn-primary btn-sm" onclick="go('ediciones')">Preparar formatos</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- VIEW: Observaciones -->
        <section class="view" id="view-observaciones">
            <div class="hero">
                <div>
                    <span class="hero-tag">Lectura editorial</span>
                    <h1>Observaciones del <em>manuscrito</em>.</h1>
                    <p>Compará cada pasaje y decidí qué cambio pertenece verdaderamente a la obra.</p>
                </div>
            </div>
            <div id="findings-list">
                <div class="empty"><p>Elegí una obra con revisión ejecutada para ver sus observaciones.</p></div>
            </div>
            <div id="findings-actions" style="display:none; margin-top:24px; display:flex; gap:12px;">
                <button class="btn btn-success btn-lg" onclick="submitAllDecisions()">Guardar todas las decisiones</button>
            </div>
        </section>

        <!-- VIEW: Ediciones listas -->
        <section class="view" id="view-ediciones">
            <div class="hero">
                <div>
                    <span class="hero-tag">Obra terminada</span>
                    <h1>Ediciones listas para <em>compartir</em>.</h1>
                    <p>Elegí la forma en que la obra llegará a sus lectores.</p>
                </div>
                <div class="hero-aside">
                    <div style="display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end">
                        <span class="badge badge-aprobada">PDF · Impresión y lectura</span>
                        <span class="badge badge-revisado">HTML · Lectura en la web</span>
                        <span class="badge badge-exportada">Libro interactivo</span>
                    </div>
                </div>
            </div>

            <div class="downloads-grid">
                <div class="download-card">
                    <div class="download-icon pdf">A4</div>
                    <h3>Libro para imprimir</h3>
                    <p>Una edición cuidada para conservar, leer en papel o enviar a imprenta.</p>
                    <button class="btn btn-primary" onclick="downloadExport('pdf')">Descargar</button>
                </div>
                <div class="download-card">
                    <div class="download-icon html">Aa</div>
                    <h3>Lectura en pantalla</h3>
                    <p>Una edición cómoda y adaptable para leer desde cualquier dispositivo.</p>
                    <button class="btn btn-primary" onclick="downloadExport('html')">Descargar</button>
                </div>
                <div class="download-card">
                    <div class="download-icon appbook">✦</div>
                    <h3>Libro interactivo</h3>
                    <p>La obra organizada para incorporar audio, notas, imágenes y recorridos de lectura.</p>
                    <button class="btn btn-primary" onclick="downloadExport('appbook')">Descargar</button>
                </div>
            </div>
        </section>
    </div>
</div>

<!-- Modal: obra creada -->
<div class="modal-backdrop" id="modal-created">
    <div class="modal">
        <h2>La obra fue creada</h2>
        <p>El manuscrito ya tiene un lugar en la mesa editorial.</p>
        <div class="modal-details" id="modal-details"></div>
        <div class="modal-actions">
            <button class="btn btn-secondary" onclick="closeModal('modal-created')">Cerrar</button>
            <button class="btn btn-primary" onclick="openCreatedWork()">Abrir la obra</button>
        </div>
    </div>
</div>

<div class="toast-container" id="toast-container"></div>

<script>
// ===== State =====
const state = {
    works: [],
    currentWork: null,
    decisions: {}, // finding_id -> {status, reason}
    createdWorkId: null,
};

// ===== Navigation =====
function go(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('#sidebar-menu a').forEach(a => a.classList.remove('active'));
    const view = document.getElementById('view-' + viewName);
    if (view) view.classList.add('active');
    const link = document.querySelector('#sidebar-menu a[data-view="' + viewName + '"]');
    if (link) link.classList.add('active');
    const labels = {
        mesa: 'La mesa', nueva: 'Nueva obra', obra: 'Obra abierta',
        talleres: 'Talleres', observaciones: 'Observaciones', ediciones: 'Ediciones listas'
    };
    document.getElementById('topbar-menu-chip').textContent = labels[viewName] || 'Menú';
    if (viewName === 'mesa') loadWorks();
    if (viewName === 'observaciones' && state.currentWork) renderFindings();
    window.scrollTo(0, 0);
}

document.querySelectorAll('#sidebar-menu a').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); go(a.dataset.view); });
});

// ===== Toast =====
function toast(kind, title, message) {
    const container = document.getElementById('toast-container');
    const icons = { success: '✓', error: '✕', info: 'ⓘ' };
    const el = document.createElement('div');
    el.className = 'toast ' + kind;
    el.innerHTML = '<div class="toast-icon">' + (icons[kind] || '') + '</div>' +
        '<div class="toast-body"><div class="toast-title">' + title + '</div>' +
        '<div class="toast-message">' + message + '</div></div>';
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateX(400px)'; }, 4000);
    setTimeout(() => el.remove(), 4500);
}

// ===== Modal =====
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

// ===== API =====
async function api(path, opts = {}) {
    try {
        const r = await fetch(path, opts);
        const text = await r.text();
        let data;
        try { data = JSON.parse(text); } catch { data = { raw: text }; }
        if (!r.ok) throw new Error(data.detail || ('HTTP ' + r.status));
        return data;
    } catch (err) {
        toast('error', 'Error', err.message);
        throw err;
    }
}

// ===== Works =====
async function loadWorks() {
    try {
        const data = await api('/api/projects');
        state.works = data.projects || [];
        renderWorks();
        updateStats();
    } catch (e) {
        document.getElementById('works-grid').innerHTML =
            '<div class="empty"><p>No se pudieron cargar las obras.</p></div>';
    }
}

function statusLabel(s) {
    return { borrador: 'Borrador', revisado: 'Leída', aprobado: 'Aprobada',
             exportado: 'Exportada', missing: 'No disponible' }[s] || s;
}
function statusBadgeClass(s) {
    return { borrador: 'badge-borrador', revisado: 'badge-leida', aprobado: 'badge-aprobada',
             exportado: 'badge-exportada', missing: 'badge-missing' }[s] || 'badge-borrador';
}

function renderWorks() {
    const grid = document.getElementById('works-grid');
    if (!state.works.length) {
        grid.innerHTML = '<div class="empty"><h3>Todavía no hay obras</h3><p>Creá la primera desde <em>Nueva obra</em>.</p></div>';
        return;
    }
    grid.innerHTML = state.works.map(w => {
        const s = w.status;
        const desc = {
            borrador: 'El manuscrito fue recibido. Falta ejecutar la lectura editorial.',
            revisado: 'La lectura editorial terminó. Falta revisar las observaciones y aprobar la edición.',
            aprobado: 'La edición fue aprobada y ya puede prepararse para imprimir, leer o publicar.',
            exportado: 'La obra fue publicada y sus ediciones están listas para compartir.',
            missing: 'El proyecto no está disponible en el sistema.',
        }[s] || '';
        const action = (s === 'borrador') ? { lbl: 'Continuar la lectura', fn: 'openWork' }
                     : (s === 'revisado') ? { lbl: 'Continuar la lectura', fn: 'openWork' }
                     : (s === 'aprobado' || s === 'exportado') ? { lbl: 'Ver ediciones', fn: 'openWorkEdiciones' }
                     : { lbl: 'Abrir', fn: 'openWork' };
        return '<div class="work-card">' +
            '<div class="work-card-top"><span class="badge ' + statusBadgeClass(s) + '">' + statusLabel(s) + '</span></div>' +
            '<h3>' + escapeHtml(w.title) + '</h3>' +
            '<p>' + desc + '</p>' +
            '<div class="work-card-footer">' +
                '<span style="font-size:0.75rem;color:var(--text-tertiary)">' +
                    (w.word_count ? w.word_count + ' palabras' : '') +
                '</span>' +
                '<button class="btn btn-primary btn-sm" onclick="' + action.fn + '(\'' + w.id + '\')">' + action.lbl + '</button>' +
            '</div></div>';
    }).join('');
}

function updateStats() {
    const works = state.works;
    document.getElementById('stat-works').textContent = works.length;
    const needs = works.filter(w => w.status === 'borrador' || w.status === 'revisado').length;
    document.getElementById('stat-works-sub').textContent = needs + ' requieren atención';
    // findings + exports: sum across works (lightweight: use status as proxy)
    const pendingFindings = works.filter(w => w.status === 'revisado').length * 3; // approx
    document.getElementById('stat-findings').textContent = pendingFindings;
    const exports = works.filter(w => w.status === 'exportado').length;
    document.getElementById('stat-exports').textContent = exports;
}

async function openWork(id) {
    try {
        const w = await api('/api/projects/' + id);
        state.currentWork = w;
        renderWorkDetail();
        go('obra');
    } catch {}
}

function openWorkEdiciones(id) {
    openWork(id).then(() => setTimeout(() => go('ediciones'), 100));
}

function renderWorkDetail() {
    const w = state.currentWork;
    if (!w) {
        document.getElementById('obra-empty').style.display = '';
        document.getElementById('obra-content').style.display = 'none';
        return;
    }
    document.getElementById('obra-empty').style.display = 'none';
    document.getElementById('obra-content').style.display = '';

    document.getElementById('obra-title').textContent = w.title;
    const statusText = {
        borrador: 'El texto fue recibido. Ejecutá la lectura editorial para continuar.',
        revisado: 'El título y los capítulos fueron reconocidos sin alterar el texto. La lectura editorial está completa y la obra espera tus decisiones.',
        aprobado: 'La edición fue aprobada. Prepará las ediciones finales.',
        exportado: 'La obra fue publicada. Las ediciones están listas.',
    }[w.status] || '';
    document.getElementById('obra-status-text').textContent = statusText;
    const badge = document.getElementById('obra-badge');
    badge.className = 'badge ' + statusBadgeClass(w.status);
    badge.textContent = statusLabel(w.status);

    // Progress
    const hasFindings = (w.findings && w.findings.length) > 0;
    const hasReview = hasFindings || ['revisado', 'aprobado', 'exportado'].includes(w.status);
    const hasDecisions = (w.decisions && w.decisions.length) > 0;
    const hasApproval = !!w.approval;
    const hasExports = w.exports && Object.keys(w.exports).length > 0;

    const steps = [
        { label: 'Ingreso', sub: 'Texto recibido', done: true },
        { label: 'Lectura', sub: hasReview ? w.findings.length + ' observaciones' : 'Pendiente', done: hasReview, active: !hasReview },
        { label: 'Aprobación', sub: hasApproval ? 'Aprobada' : (hasDecisions ? 'Decisiones listas' : 'Pendiente'), done: hasApproval, active: hasReview && !hasApproval, pending: !hasReview },
        { label: 'Ediciones', sub: hasExports ? 'Publicadas' : 'En espera', done: hasExports, active: hasApproval && !hasExports, pending: !hasApproval },
    ];
    document.getElementById('obra-steps').innerHTML = steps.map((s, i) => {
        const cls = s.done ? 'step done' : s.active ? 'step active' : 'step pending';
        const icon = s.done ? '✓' : (i + 1);
        return '<div class="' + cls + '"><div class="step-icon">' + icon + '</div>' +
            '<div><div class="step-label">' + s.label + '</div>' +
            '<div class="step-sub">' + s.sub + '</div></div></div>';
    }).join('');

    document.getElementById('obra-parts').textContent = w.chapter_count || '—';
    document.getElementById('obra-lang').textContent = ({es:'Español', en:'Inglés', pt:'Portugués'})[w.language] || w.language;
    document.getElementById('obra-situacion').textContent = statusLabel(w.status);

    // Buttons
    document.getElementById('btn-findings').disabled = !hasReview;
    document.getElementById('btn-approve').disabled = !hasDecisions && !hasApproval;
}

// ===== Review =====
async function runReview() {
    if (!state.currentWork) return;
    const btn = document.getElementById('btn-review');
    const old = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Ejecutando lectura…';
    try {
        const r = await api('/api/projects/' + state.currentWork.id + '/review', { method: 'POST' });
        toast('success', 'Lectura completada', r.message || 'La revisión terminó.');
        await openWork(state.currentWork.id);
    } catch {}
    finally { btn.disabled = false; btn.innerHTML = old; }
}

// ===== Findings =====
async function renderFindings() {
    const list = document.getElementById('findings-list');
    const actions = document.getElementById('findings-actions');
    if (!state.currentWork) {
        list.innerHTML = '<div class="empty"><p>Elegí una obra con revisión ejecutada para ver sus observaciones.</p></div>';
        actions.style.display = 'none';
        return;
    }
    const findings = state.currentWork.findings || [];
    if (!findings.length) {
        list.innerHTML = '<div class="empty"><h3>Sin observaciones</h3><p>La revisión no produjo observaciones para esta obra.</p></div>';
        actions.style.display = 'none';
        return;
    }
    state.decisions = {};
    (state.currentWork.decisions || []).forEach(d => { state.decisions[d.finding_id] = d; });
    list.innerHTML = findings.map((f, i) => {
        const existing = state.decisions[f.finding_id];
        return '<div class="finding-card" id="finding-' + f.finding_id + '">' +
            '<div class="finding-head">' +
                '<div class="finding-type">' +
                    '<div class="finding-type-name">' + escapeHtml(f.finding_type || f.classification || 'Observación') + '</div>' +
                    '<div class="finding-id">' + (f.finding_id || ('O-' + String(i+1).padStart(3,'0'))) + '</div>' +
                '</div>' +
            '</div>' +
            '<div class="text-block original"><span class="text-block-label">Texto original</span>' + escapeHtml(f.evidence || '') + '</div>' +
            '<div class="text-block proposal"><span class="text-block-label">Propuesta</span>' + escapeHtml(f.proposal || '') + '</div>' +
            (f.classification ? '<div class="finding-rationale">' + escapeHtml(f.classification) + '</div>' : '') +
            '<div class="finding-actions">' +
                '<button class="btn btn-danger btn-sm" onclick="setDecision(\'' + f.finding_id + '\', \'rejected\')">Descartar</button>' +
                '<button class="btn btn-success btn-sm" onclick="setDecision(\'' + f.finding_id + '\', \'accepted\')">Aceptar</button>' +
                (existing ? '<span class="badge ' + (existing.status === 'accepted' ? 'badge-aprobada' : 'badge-missing') + '" style="margin-left:8px">' +
                    (existing.status === 'accepted' ? 'Aceptada' : 'Descartada') + '</span>' : '') +
            '</div></div>';
    }).join('');
    actions.style.display = 'flex';
}

function setDecision(findingId, status) {
    const reason = status === 'accepted'
        ? 'Corrección aceptada por criterio editorial.'
        : 'Propuesta descartada por criterio editorial.';
    state.decisions[findingId] = { finding_id: findingId, status: status, reason: reason };
    const card = document.getElementById('finding-' + findingId);
    if (!card) return;
    const actions = card.querySelector('.finding-actions');
    // Re-render action area with badge
    const existingBadge = actions.querySelector('.badge');
    if (existingBadge) existingBadge.remove();
    const badge = document.createElement('span');
    badge.className = 'badge ' + (status === 'accepted' ? 'badge-aprobada' : 'badge-missing');
    badge.style.marginLeft = '8px';
    badge.textContent = status === 'accepted' ? 'Aceptada' : 'Descartada';
    actions.appendChild(badge);
}

async function submitAllDecisions() {
    if (!state.currentWork) return;
    const findings = state.currentWork.findings || [];
    const decisions = Object.values(state.decisions);
    if (decisions.length !== findings.length) {
        toast('info', 'Decisiones incompletas', 'Aceptá o descartá todas las observaciones antes de continuar.');
        return;
    }
    try {
        const r = await api('/api/projects/' + state.currentWork.id + '/decisions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(decisions),
        });
        toast('success', 'Decisiones guardadas', (r.accepted || 0) + ' aceptadas · ' + (r.rejected || 0) + ' descartadas');
        await openWork(state.currentWork.id);
    } catch {}
}

// ===== Approval =====
async function approveEdition() {
    if (!state.currentWork) return;
    const w = state.currentWork;
    if (!w.approval) {
        toast('info', 'Aprobación', 'Primero guardá todas las decisiones editoriales.');
        return;
    }
    const approval = {
        ...w.approval,
        status: 'approved',
        actor_id: 'actor.editora',
        reason: w.approval.reason || 'Aprobación editorial desde la consola.',
        decided_at: new Date().toISOString(),
    };
    const btn = document.getElementById('btn-approve');
    const old = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Publicando…';
    try {
        const r = await api('/api/projects/' + w.id + '/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(approval),
        });
        toast('success', 'Edición aprobada', 'La obra fue publicada.');
        await openWork(w.id);
        go('ediciones');
    } catch {}
    finally { btn.disabled = false; btn.innerHTML = old; }
}

// ===== Downloads =====
function downloadExport(fmt) {
    if (!state.currentWork) { toast('info', 'Descarga', 'Abrí una obra aprobada para descargar.'); return; }
    if (!state.currentWork.exports || !state.currentWork.exports[fmt === 'appbook' ? 'appbook.json' : fmt]) {
        toast('info', 'Descarga', 'Esta edición todavía no está disponible. Aprobá la edición primero.');
        return;
    }
    window.open('/api/projects/' + state.currentWork.id + '/download/' + fmt, '_blank');
}

// ===== Create work =====
let selectedFile = null;
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('f-file');

fileInput.addEventListener('change', e => {
    if (e.target.files.length) pickFile(e.target.files[0]);
});
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', e => {
    e.preventDefault(); dropzone.classList.remove('drag');
    if (e.dataTransfer.files.length) pickFile(e.dataTransfer.files[0]);
});

function pickFile(f) {
    selectedFile = f;
    document.getElementById('dropzone-file-name').textContent = f.name + ' · ' + Math.round(f.size/1024) + ' KB';
    document.getElementById('dropzone-file').classList.add('visible');
}
function clearFile() {
    selectedFile = null; fileInput.value = '';
    document.getElementById('dropzone-file').classList.remove('visible');
}

document.getElementById('new-work-form').addEventListener('submit', async e => {
    e.preventDefault();
    if (!selectedFile) { toast('error', 'Falta el manuscrito', 'Acercá un archivo de texto.'); return; }
    const btn = document.getElementById('btn-create');
    const lbl = document.getElementById('btn-create-label');
    const sp = document.getElementById('btn-create-spinner');
    btn.disabled = true; lbl.textContent = 'Creando la obra…'; sp.style.display = '';
    try {
        const fd = new FormData();
        fd.append('title', document.getElementById('f-title').value);
        fd.append('author', document.getElementById('f-author').value);
        fd.append('language', document.getElementById('f-language').value);
        fd.append('manuscript', selectedFile);
        const r = await api('/api/projects', { method: 'POST', body: fd });
        state.createdWorkId = r.id;
        document.getElementById('modal-details').innerHTML =
            '<div class="modal-details-row"><span class="modal-details-label">Título</span><span class="modal-details-value">' + escapeHtml(r.title) + '</span></div>' +
            '<div class="modal-details-row"><span class="modal-details-label">Autoría</span><span class="modal-details-value">' + escapeHtml(document.getElementById('f-author').value || 'Sin indicar') + '</span></div>' +
            '<div class="modal-details-row"><span class="modal-details-label">Archivo</span><span class="modal-details-value">' + escapeHtml(selectedFile.name) + '</span></div>';
        openModal('modal-created');
        toast('success', 'Obra creada', r.title);
        document.getElementById('new-work-form').reset();
        clearFile();
        loadWorks();
    } catch {}
    finally { btn.disabled = false; lbl.textContent = 'Crear la obra'; sp.style.display = 'none'; }
});

function openCreatedWork() {
    closeModal('modal-created');
    if (state.createdWorkId) openWork(state.createdWorkId);
}

// ===== Utils =====
function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ===== Init =====
loadWorks();
</script>
</body>
</html>
'''
