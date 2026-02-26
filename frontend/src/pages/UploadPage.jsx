import { useState, useCallback, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { Upload, Trash2, RefreshCw, X, Download } from 'lucide-react'
import { exportToExcel, formatCandidatesForExcel } from '../utils/excelUtils'

/* ─── Single chip ─────────────────────────────────────────────────────────── */
function Chip({ text }) {
    return (
        <span style={{
            background: 'rgba(33,158,188,0.12)', border: '1px solid rgba(33,158,188,0.25)',
            borderRadius: 5, padding: '2px 7px', fontSize: '0.73rem',
            color: 'var(--sky-dim)', whiteSpace: 'nowrap', lineHeight: '1.7',
            display: 'inline-block', maxWidth: '100%', overflow: 'hidden',
            textOverflow: 'ellipsis',
        }}>{text}</span>
    )
}

/* ─── Collapsible popup cell ──────────────────────────────────────────────── */
function ExpandableCell({ value, onEdit }) {
    const [open, setOpen] = useState(false)
    const [pos, setPos] = useState({ top: 0, left: 0 })
    const btnRef = useRef(null)

    const items = value ? String(value).split(',').map(s => s.trim()).filter(Boolean) : []

    const openPopup = (e) => {
        e.stopPropagation()
        const rect = (btnRef.current || e.currentTarget).getBoundingClientRect()
        const POPUP_H = 230  // estimated popup height
        const POPUP_W = 310  // popup width

        // If not enough space below → show above the button
        const top = (rect.bottom + POPUP_H + 6 > window.innerHeight)
            ? rect.top - POPUP_H - 6
            : rect.bottom + 6

        // Clamp left so popup doesn't go off the right edge
        const left = Math.min(rect.left, window.innerWidth - POPUP_W - 10)

        setPos({ top, left })
        setOpen(true)
    }

    useEffect(() => {
        if (!open) return
        const close = () => setOpen(false)
        document.addEventListener('click', close)
        return () => document.removeEventListener('click', close)
    }, [open])

    if (items.length === 0) return <span style={{ opacity: 0.35 }}>—</span>

    return (
        <>
            {/* Always inside the td — compact single row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, overflow: 'hidden' }}>
                <span style={{
                    background: 'rgba(33,158,188,0.12)', border: '1px solid rgba(33,158,188,0.25)',
                    borderRadius: 5, padding: '2px 7px', fontSize: '0.73rem',
                    color: 'var(--sky-dim)', whiteSpace: 'nowrap', overflow: 'hidden',
                    textOverflow: 'ellipsis', lineHeight: '1.7', maxWidth: 'calc(100% - 64px)',
                    display: 'inline-block',
                }}>{items[0]}</span>

                {items.length > 1 && (
                    <span ref={btnRef}
                        onClick={openPopup}
                        style={{
                            background: 'rgba(255,183,3,0.13)', border: '1px solid rgba(255,183,3,0.35)',
                            borderRadius: 5, padding: '2px 7px', fontSize: '0.7rem',
                            color: 'var(--gold)', cursor: 'pointer', whiteSpace: 'nowrap',
                            lineHeight: '1.7', fontFamily: 'var(--fh)', fontWeight: 700,
                            flexShrink: 0,
                        }}>
                        +{items.length - 1}
                    </span>
                )}
            </div>

            {/* Popup — fixed to viewport, never inside table layout */}
            {open && (
                <div
                    onClick={e => e.stopPropagation()}
                    style={{
                        position: 'fixed', top: pos.top, left: pos.left, zIndex: 9999,
                        background: 'rgba(1,22,39,0.98)', border: '1px solid rgba(33,158,188,0.4)',
                        borderRadius: 12, padding: '14px 16px', width: 310,
                        boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
                    }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <span style={{
                            fontSize: '0.74rem', color: 'var(--gold)', fontFamily: 'var(--fh)',
                            fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05rem'
                        }}>
                            All ({items.length})
                        </span>
                        <button onClick={() => setOpen(false)}
                            style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: 2 }}>
                            <X size={14} />
                        </button>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
                        {items.map((s, i) => <Chip key={i} text={s} />)}
                    </div>

                    <div style={{
                        marginTop: 10, borderTop: '1px solid rgba(33,158,188,0.1)',
                        paddingTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                        <span style={{ fontSize: '0.7rem', color: 'rgba(142,202,230,0.4)' }}>
                            Double-click cell to edit full text
                        </span>
                        <button onClick={() => { setOpen(false); onEdit() }}
                            style={{
                                background: 'rgba(255,183,3,0.1)', border: '1px solid rgba(255,183,3,0.3)',
                                borderRadius: 6, color: 'var(--gold)', fontSize: '0.72rem', cursor: 'pointer',
                                padding: '3px 10px', fontFamily: 'var(--fh)', fontWeight: 700
                            }}>
                            ✏ Edit
                        </button>
                    </div>
                </div>
            )}
        </>
    )
}

/* ─── Column config ───────────────────────────────────────────────────────── */
const COLS = [
    { key: 'full_name', label: 'Name', pct: '12%' },
    { key: 'total_experience', label: 'Total\u00A0Exp', pct: '7%' },
    { key: 'pega_experience', label: 'Pega\u00A0Exp', pct: '7%' },
    { key: 'skills', label: 'Skills', pct: '13%' },
    { key: 'certifications', label: 'Certifications', pct: '12%' },
    { key: 'ctc', label: 'CTC', pct: '6%' },
    { key: 'notice_period', label: 'Notice', pct: '7%' },
    { key: 'current_organization', label: 'Company', pct: '11%' },
    { key: 'email', label: 'Email', pct: '13%' },
    { key: 'phone', label: 'Phone', pct: '8%' },
    { key: '_del', label: '', pct: '4%' },
]

const TH = {
    padding: '11px 10px',
    textAlign: 'left',
    fontFamily: 'var(--fh)', fontWeight: 800, fontSize: '0.73rem',
    color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.05rem',
    borderBottom: '2px solid var(--border)', background: 'rgba(2,48,71,0.97)',
    /* prevent th text from overflowing into next header */
    overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
}

const TD_BASE = {
    padding: '10px 10px',
    verticalAlign: 'top',
    borderBottom: '1px solid rgba(33,158,188,0.07)',
    /* ALL cells clip — nothing bleeds into adjacent column */
    overflow: 'hidden',
}

/* ─── Page ────────────────────────────────────────────────────────────────── */
export default function UploadPage() {
    const [candidates, setCandidates] = useState([])
    const [progress, setProgress] = useState([])
    const [toast, setToast] = useState(null)
    const [editCell, setEditCell] = useState(null)
    const [editVal, setEditVal] = useState('')

    const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3500) }
    const load = () => axios.get('/api/candidates').then(r => setCandidates(r.data)).catch(() => { })
    useEffect(() => { load() }, [])

    const onDrop = useCallback(async (files) => {
        if (!files.length) return
        setProgress(files.map(f => ({ name: f.name, status: 'pending', percent: 0 })))
        for (let i = 0; i < files.length; i++) {
            const fd = new FormData(); fd.append('file', files[i])
            setProgress(p => p.map((x, idx) => idx === i ? { ...x, status: 'processing', percent: 10 } : x))
            try {
                await axios.post('/api/upload', fd, {
                    onUploadProgress: ev => {
                        const pct = Math.round((ev.loaded / ev.total) * 70)
                        setProgress(p => p.map((x, idx) => idx === i ? { ...x, percent: 10 + pct } : x))
                    }
                })
                setProgress(p => p.map((x, idx) => idx === i ? { ...x, status: 'done', percent: 100 } : x))
            } catch {
                setProgress(p => p.map((x, idx) => idx === i ? { ...x, status: 'error', percent: 0 } : x))
            }
        }
        load(); showToast(`${files.length} resume(s) analyzed!`)
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
        multiple: true,
    })

    const startEdit = (ri, col, val) => { setEditCell({ row: ri, col }); setEditVal(String(val || '')) }
    const saveEdit = async (ri) => {
        const c = candidates[ri]; if (!c?.id) { setEditCell(null); return }
        try {
            await axios.put(`/api/candidates/${c.id}`, { [editCell.col]: editVal })
            setCandidates(prev => prev.map((row, i) => i === ri ? { ...row, [editCell.col]: editVal } : row))
            showToast('Saved!')
        } catch { showToast('Save failed', 'error') }
        setEditCell(null)
    }
    const del = async (id) => {
        if (!window.confirm('Delete this candidate?')) return
        try { await axios.delete(`/api/candidates/${id}`); setCandidates(p => p.filter(c => c.id !== id)); showToast('Deleted') }
        catch { showToast('Delete failed', 'error') }
    }

    return (
        <div style={{ padding: '2rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '2rem' }}>

            {/* Drop Zone */}
            <div className="card">
                <div className="card-title"><Upload size={17} /> Upload Resumes</div>
                <div {...getRootProps()} className={`dropzone${isDragActive ? ' active' : ''}`}>
                    <input {...getInputProps()} />
                    <div className="dropzone-icon">📄</div>
                    <div className="dropzone-text">
                        {isDragActive ? <strong>Drop here…</strong>
                            : <><strong>Drag & drop</strong> PDF / DOCX resumes, or click to browse</>}
                    </div>
                </div>
                {progress.length > 0 && (
                    <div style={{ marginTop: '1.4rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                        {progress.map((p, i) => (
                            <div key={i}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>{p.name}</span>
                                    <span className={`badge ${p.status === 'done' ? 'badge-green' : p.status === 'error' ? 'badge-red' : 'badge-sky'}`}>
                                        {p.status === 'done' ? '✓ Done' : p.status === 'error' ? '✗ Error' : 'Processing…'}
                                    </span>
                                </div>
                                <div className="progress-bar"><div className="progress-fill" style={{ width: `${p.percent}%` }} /></div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Table */}
            <div className="card" style={{ flex: 1 }}>
                <div className="section-header">
                    <div className="section-title">👥 Candidate Details</div>
                    <div style={{ display: 'flex', gap: 10 }}>
                        <button
                            className="btn btn-secondary"
                            style={{ gap: 6 }}
                            onClick={() => exportToExcel(formatCandidatesForExcel(candidates), 'all_candidates_details.xlsx')}
                        >
                            <Download size={14} /> Download Excel
                        </button>
                        <button className="btn btn-secondary" onClick={load} style={{ gap: 6 }}>
                            <RefreshCw size={14} /> Refresh
                        </button>
                    </div>
                </div>

                {candidates.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-dim)' }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>📋</div>
                        <p>No candidates yet. Upload resumes to get started.</p>
                    </div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto', borderRadius: 10, border: '1px solid var(--border)' }}>
                            <table style={{ width: '100%', minWidth: 860, tableLayout: 'fixed', borderCollapse: 'collapse', fontSize: '0.83rem' }}>
                                <colgroup>
                                    {COLS.map(c => <col key={c.key} style={{ width: c.pct }} />)}
                                </colgroup>
                                <thead>
                                    <tr>
                                        {COLS.map(c => <th key={c.key} style={TH} title={c.label}>{c.label}</th>)}
                                    </tr>
                                </thead>
                                <tbody>
                                    {candidates.map((row, ri) => (
                                        <tr key={row.id || ri}
                                            style={{ background: ri % 2 === 0 ? 'rgba(2,48,71,0.25)' : 'transparent', transition: 'background 0.15s' }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(33,158,188,0.07)'}
                                            onMouseLeave={e => e.currentTarget.style.background = ri % 2 === 0 ? 'rgba(2,48,71,0.25)' : 'transparent'}
                                        >
                                            {COLS.map(({ key }) => {
                                                /* ── Delete button ── */
                                                if (key === '_del') return (
                                                    <td key={key} style={{ ...TD_BASE, textAlign: 'center' }}>
                                                        <button className="btn btn-danger" style={{ padding: '4px 7px' }} onClick={() => del(row.id)}>
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </td>
                                                )

                                                const isEditing = editCell?.row === ri && editCell?.col === key
                                                const val = row[key] ?? ''
                                                const isExp = key === 'total_experience' || key === 'pega_experience'
                                                const isExpandable = key === 'skills' || key === 'certifications'

                                                /* ── Inline edit mode ── */
                                                if (isEditing) return (
                                                    <td key={key} style={TD_BASE}>
                                                        <input autoFocus value={editVal}
                                                            onChange={e => setEditVal(e.target.value)}
                                                            onBlur={() => saveEdit(ri)}
                                                            onKeyDown={e => { if (e.key === 'Enter') saveEdit(ri); if (e.key === 'Escape') setEditCell(null) }}
                                                            style={{
                                                                background: 'rgba(255,183,3,0.1)', border: '1px solid var(--gold)',
                                                                borderRadius: 6, padding: '4px 8px', color: '#fff', width: '100%',
                                                                fontFamily: 'var(--fb)', fontSize: '0.82rem', outline: 'none'
                                                            }}
                                                        />
                                                    </td>
                                                )

                                                /* ── Expandable (skills / certs) — td stays overflow:hidden ── */
                                                if (isExpandable) return (
                                                    <td key={key} style={{ ...TD_BASE }} onDoubleClick={() => startEdit(ri, key, val)}>
                                                        <ExpandableCell value={val} onEdit={() => startEdit(ri, key, val)} />
                                                    </td>
                                                )

                                                /* ── Regular cells ── */
                                                const display = isExp ? (val !== '' && val != null ? `${val} yrs` : '—') : (val || '—')
                                                return (
                                                    <td key={key} onDoubleClick={() => startEdit(ri, key, val)} style={{
                                                        ...TD_BASE,
                                                        color: key === 'full_name' ? 'var(--gold)' : key === 'email' ? 'var(--sky-dim)' : 'var(--text)',
                                                        fontWeight: key === 'full_name' ? 700 : undefined,
                                                        /* overflow already hidden via TD_BASE — text clips cleanly */
                                                        whiteSpace: key === 'full_name' || key === 'current_organization' || key === 'email'
                                                            ? 'normal' : 'nowrap',
                                                        wordBreak: key === 'email' ? 'break-all' : undefined,
                                                        cursor: 'text',
                                                    }}>
                                                        {key === 'full_name' && row.filename ? (
                                                            <a
                                                                href={`/static/${row.filename}`}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                style={{ color: 'inherit', textDecoration: 'none', borderBottom: '1px dashed transparent', transition: 'all 0.2s' }}
                                                                onMouseEnter={e => e.currentTarget.style.borderBottomColor = 'var(--gold)'}
                                                                onMouseLeave={e => e.currentTarget.style.borderBottomColor = 'transparent'}
                                                                title={`Download ${row.filename}`}
                                                            >
                                                                {String(display)}
                                                            </a>
                                                        ) : String(display)}
                                                    </td>
                                                )
                                            })}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <p style={{ marginTop: '0.6rem', fontSize: '0.75rem', color: 'rgba(142,202,230,0.38)' }}>
                            💡 Click <strong style={{ color: 'var(--gold)' }}>+N</strong> to expand Skills / Certs · Double-click any cell to edit
                        </p>
                    </>
                )}
            </div>

            {toast && (
                <div className="toast-container">
                    <div className={`toast ${toast.type}`}>{toast.msg}</div>
                </div>
            )}
        </div>
    )
}
