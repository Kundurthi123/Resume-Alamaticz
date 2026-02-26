import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, Cell
} from 'recharts'
import { Users, Clock, Download } from 'lucide-react'
import { exportToExcel, formatCandidatesForExcel } from '../utils/excelUtils'

function SkillBadges({ skills }) {
    if (!skills) return <span style={{ opacity: 0.35 }}>—</span>
    const list = String(skills).split(',').map(s => s.trim()).filter(Boolean)
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {list.map((s, i) => (
                <span key={i} style={{
                    background: 'rgba(33,158,188,0.12)', border: '1px solid rgba(33,158,188,0.25)',
                    borderRadius: 5, padding: '1px 7px', fontSize: '0.73rem',
                    color: 'var(--sky-dim)', whiteSpace: 'nowrap', lineHeight: '1.6',
                }}>{s}</span>
            ))}
        </div>
    )
}

const COLORS = ['#FB8500', '#FFB703', '#219EBC', '#8ECAE6', '#023047']

export default function DashboardPage() {
    const [candidates, setCandidates] = useState([])
    const [loading, setLoading] = useState(true)
    const [filterType, setFilterType] = useState('all') // 'all' | 'immediate'
    const summaryRef = useRef(null)

    useEffect(() => {
        axios.get('/api/candidates')
            .then(r => setCandidates(r.data))
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

    const totalCandidates = candidates.length
    const immediate = candidates.filter(c =>
        (c.notice_period || '').toLowerCase().includes('immediate')
    ).length

    const filteredCandidates = filterType === 'immediate'
        ? candidates.filter(c => (c.notice_period || '').toLowerCase().includes('immediate'))
        : candidates

    const handleKpiClick = (type) => {
        setFilterType(type)
        summaryRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    const expChartData = candidates.map(c => ({
        name: (c.full_name || c.filename || '?').split(' ')[0],
        'Total Exp': +c.total_experience || 0,
        'Pega Exp': +c.pega_experience || 0,
    }))

    const noticeCounts = {}
    candidates.forEach(c => {
        const k = (c.notice_period || '').trim()
        if (k) noticeCounts[k] = (noticeCounts[k] || 0) + 1
    })
    const noticeData = Object.entries(noticeCounts).map(([name, value]) => ({ name, value }))

    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload?.length) return null
        return (
            <div style={{
                background: 'rgba(1,22,39,0.95)', border: '1px solid rgba(255,183,3,0.3)',
                borderRadius: 10, padding: '10px 14px', fontSize: '0.84rem'
            }}>
                <p style={{ color: 'var(--gold)', marginBottom: 6, fontWeight: 700 }}>{label}</p>
                {payload.map(p => (
                    <p key={p.name} style={{ color: p.color }}>{p.name}: <strong>{p.value} yrs</strong></p>
                ))}
            </div>
        )
    }

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
            <div className="spinner" style={{ width: 40, height: 40 }} />
        </div>
    )

    return (
        <div style={{ padding: '2rem', flex: 1 }}>

            {/* KPIs */}
            <div className="kpi-grid">
                {[
                    { label: 'Total Candidates', value: totalCandidates, Icon: Users, type: 'all' },
                    { label: 'Immediate Joiners', value: immediate, Icon: Clock, type: 'immediate' },
                ].map(({ label, value, Icon, type }) => (
                    <div
                        className={`kpi-card ${filterType === type ? 'active' : ''}`}
                        key={label}
                        onClick={() => handleKpiClick(type)}
                        style={{ cursor: 'pointer', border: filterType === type ? '1px solid var(--gold)' : '' }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
                            <div style={{
                                width: 42, height: 42, background: 'rgba(255,183,3,0.12)',
                                borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <Icon size={20} color="var(--gold)" />
                            </div>
                        </div>
                        <div className="kpi-value">{value}</div>
                        <div className="kpi-label">{label}</div>
                    </div>
                ))}
            </div>

            {/* Empty state */}
            {candidates.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-dim)' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
                    <p style={{ fontSize: '1.1rem', fontFamily: 'var(--fh)', color: 'var(--gold)' }}>No Data Yet</p>
                    <p style={{ marginTop: '0.5rem' }}>Upload and analyze resumes to see insights here.</p>
                </div>
            ) : (
                <>
                    {/* Charts */}
                    <div className="charts-grid">
                        <div className="card">
                            <div className="card-title">📊 Experience</div>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={expChartData} margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="name" tick={{ fill: '#8ECAE6', fontSize: 12 }} angle={-30} textAnchor="end" />
                                    <YAxis tick={{ fill: '#8ECAE6', fontSize: 12 }} unit=" yr" />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend wrapperStyle={{ color: '#8ECAE6', fontSize: 13 }} />
                                    <Bar dataKey="Total Exp" fill="#FB8500" radius={[6, 6, 0, 0]} />
                                    <Bar dataKey="Pega Exp" fill="#FFB703" radius={[6, 6, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        <div className="card">
                            <div className="card-title">⏱ Notice Period</div>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={noticeData} margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                    <XAxis dataKey="name" tick={{ fill: '#8ECAE6', fontSize: 12 }} angle={-30} textAnchor="end" />
                                    <YAxis tick={{ fill: '#8ECAE6', fontSize: 12 }} allowDecimals={false} />
                                    <Tooltip contentStyle={{
                                        background: 'rgba(1,22,39,0.95)',
                                        border: '1px solid rgba(255,183,3,0.3)', borderRadius: 10, color: '#fff'
                                    }} />
                                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                                        {noticeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Summary Table — fixed layout, fits screen, no scroll */}
                    <div className="card" ref={summaryRef}>
                        <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                👥 {filterType === 'immediate' ? 'Immediate Joiners' : 'Candidate Summary'}
                            </div>
                            <button
                                className="btn btn-secondary"
                                style={{ fontSize: '0.75rem', padding: '6px 12px', gap: 6 }}
                                onClick={() => exportToExcel(formatCandidatesForExcel(filteredCandidates), 'hire_ai_candidates.xlsx')}
                            >
                                <Download size={14} /> Download Excel
                            </button>
                        </div>
                        <table style={{ width: '100%', tableLayout: 'fixed', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                            <colgroup>
                                <col style={{ width: '14%' }} />
                                <col style={{ width: '8%' }} />
                                <col style={{ width: '8%' }} />
                                <col style={{ width: '22%' }} />
                                <col style={{ width: '7%' }} />
                                <col style={{ width: '10%' }} />
                                <col style={{ width: '15%' }} />
                                <col style={{ width: '16%' }} />
                            </colgroup>
                            <thead>
                                <tr style={{ background: 'rgba(2,48,71,0.9)' }}>
                                    {['Name', 'Total Exp', 'Pega Exp', 'Skills', 'CTC', 'Notice Period', 'Organization', 'Email'].map(h => (
                                        <th key={h} style={{
                                            padding: '11px 12px', textAlign: 'left',
                                            fontFamily: 'var(--fh)', fontWeight: 700, fontSize: '0.78rem',
                                            color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.04rem',
                                            borderBottom: '1px solid var(--border)'
                                        }}>
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {filteredCandidates.map((c, i) => (
                                    <tr key={i} style={{
                                        borderBottom: '1px solid rgba(33,158,188,0.1)',
                                        background: i % 2 === 0 ? 'rgba(2,48,71,0.2)' : 'transparent'
                                    }}>
                                        <td style={{
                                            padding: '10px 12px', color: 'var(--gold)', fontWeight: 600,
                                            wordBreak: 'break-word', verticalAlign: 'top'
                                        }}>
                                            <a
                                                href={`/static/${c.filename}`}
                                                target="_blank"
                                                rel="noreferrer"
                                                style={{ color: 'inherit', textDecoration: 'none', borderBottom: '1px dashed transparent', transition: 'all 0.2s' }}
                                                onMouseEnter={e => e.currentTarget.style.borderBottomColor = 'var(--gold)'}
                                                onMouseLeave={e => e.currentTarget.style.borderBottomColor = 'transparent'}
                                                title={`Download ${c.filename}`}
                                            >
                                                {c.full_name || '—'}
                                            </a>
                                        </td>
                                        <td style={{ padding: '10px 12px', textAlign: 'center', verticalAlign: 'top' }}>
                                            {c.total_experience ? `${c.total_experience} yrs` : '—'}
                                        </td>
                                        <td style={{ padding: '10px 12px', textAlign: 'center', verticalAlign: 'top' }}>
                                            {c.pega_experience ? `${c.pega_experience} yrs` : '—'}
                                        </td>
                                        <td style={{ padding: '10px 12px', verticalAlign: 'top' }}>
                                            <SkillBadges skills={c.skills} />
                                        </td>
                                        <td style={{ padding: '10px 12px', verticalAlign: 'top' }}>{c.ctc || '—'}</td>
                                        <td style={{ padding: '10px 12px', verticalAlign: 'top' }}>
                                            <span className={`badge ${(c.notice_period || '').toLowerCase().includes('immediate')
                                                ? 'badge-green' : 'badge-sky'}`}>
                                                {c.notice_period || '—'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '10px 12px', wordBreak: 'break-word', verticalAlign: 'top' }}>
                                            {c.current_organization || '—'}
                                        </td>
                                        <td style={{
                                            padding: '10px 12px', color: 'var(--sky-dim)',
                                            wordBreak: 'break-all', fontSize: '0.8rem', verticalAlign: 'top'
                                        }}>
                                            {c.email || '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}
