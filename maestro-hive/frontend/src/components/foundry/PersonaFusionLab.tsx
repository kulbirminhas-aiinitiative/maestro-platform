/**
 * PersonaFusionLab - MD-3017
 *
 * Interactive UI component for combining multiple personas into hybrid agents.
 * Provides real-time preview, strategy selection, and trait visualization.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';

// Types
interface PersonaTrait {
  name: string;
  value: number;
  weight: number;
}

interface Persona {
  id: string;
  name: string;
  description: string;
  traits: PersonaTrait[];
  avatar?: string;
}

interface FusionPreview {
  previewId: string;
  sourcePersonas: string[];
  estimatedTraits: Record<string, number>;
  strategy: string;
  compatibilityScore: number;
  warnings: string[];
}

interface FusedPersona {
  id: string;
  name: string;
  sourcePersonas: string[];
  blendedTraits: Record<string, number>;
  fusionStrategy: string;
  createdAt: string;
  metadata: Record<string, unknown>;
}

type FusionStrategy =
  | 'weighted_average'
  | 'max_pooling'
  | 'min_pooling'
  | 'hierarchical'
  | 'consensus';

interface PersonaFusionLabProps {
  availablePersonas: Persona[];
  onFusionComplete?: (fusedPersona: FusedPersona) => void;
  onPreviewGenerated?: (preview: FusionPreview) => void;
  maxSelectable?: number;
  apiEndpoint?: string;
  showAdvancedOptions?: boolean;
}

// Strategy descriptions
const STRATEGY_INFO: Record<FusionStrategy, { label: string; description: string }> = {
  weighted_average: {
    label: 'Weighted Average',
    description: 'Blend traits using weighted averages for balanced results',
  },
  max_pooling: {
    label: 'Max Pooling',
    description: 'Take the maximum value for each trait - best for enhancing strengths',
  },
  min_pooling: {
    label: 'Min Pooling',
    description: 'Take the minimum value for each trait - conservative approach',
  },
  hierarchical: {
    label: 'Hierarchical',
    description: 'First selected persona takes priority for trait values',
  },
  consensus: {
    label: 'Consensus',
    description: 'Use median values for balanced, conflict-resistant blending',
  },
};

// Components
const TraitBar: React.FC<{ name: string; value: number; color?: string }> = ({
  name,
  value,
  color = '#3b82f6',
}) => (
  <div className="trait-bar">
    <div className="trait-bar-label">
      <span className="trait-name">{name}</span>
      <span className="trait-value">{(value * 100).toFixed(0)}%</span>
    </div>
    <div className="trait-bar-track">
      <div
        className="trait-bar-fill"
        style={{
          width: `${value * 100}%`,
          backgroundColor: color,
        }}
      />
    </div>
  </div>
);

const PersonaCard: React.FC<{
  persona: Persona;
  isSelected: boolean;
  onToggle: () => void;
  selectionOrder?: number;
}> = ({ persona, isSelected, onToggle, selectionOrder }) => (
  <div
    className={`persona-card ${isSelected ? 'selected' : ''}`}
    onClick={onToggle}
    role="button"
    tabIndex={0}
    onKeyPress={(e) => e.key === 'Enter' && onToggle()}
  >
    {selectionOrder !== undefined && (
      <div className="selection-badge">{selectionOrder}</div>
    )}
    <div className="persona-avatar">
      {persona.avatar ? (
        <img src={persona.avatar} alt={persona.name} />
      ) : (
        <div className="avatar-placeholder">
          {persona.name.charAt(0).toUpperCase()}
        </div>
      )}
    </div>
    <h3 className="persona-name">{persona.name}</h3>
    <p className="persona-description">{persona.description}</p>
    <div className="persona-traits">
      {persona.traits.slice(0, 3).map((trait) => (
        <TraitBar key={trait.name} name={trait.name} value={trait.value} />
      ))}
      {persona.traits.length > 3 && (
        <span className="more-traits">+{persona.traits.length - 3} more</span>
      )}
    </div>
  </div>
);

const StrategySelector: React.FC<{
  selected: FusionStrategy;
  onChange: (strategy: FusionStrategy) => void;
}> = ({ selected, onChange }) => (
  <div className="strategy-selector">
    <h4>Fusion Strategy</h4>
    <div className="strategy-options">
      {(Object.keys(STRATEGY_INFO) as FusionStrategy[]).map((strategy) => (
        <button
          key={strategy}
          className={`strategy-option ${selected === strategy ? 'active' : ''}`}
          onClick={() => onChange(strategy)}
          title={STRATEGY_INFO[strategy].description}
        >
          <span className="strategy-label">{STRATEGY_INFO[strategy].label}</span>
        </button>
      ))}
    </div>
    <p className="strategy-description">{STRATEGY_INFO[selected].description}</p>
  </div>
);

const FusionPreviewPanel: React.FC<{
  preview: FusionPreview | null;
  isLoading: boolean;
}> = ({ preview, isLoading }) => {
  if (isLoading) {
    return (
      <div className="preview-panel loading">
        <div className="loading-spinner" />
        <p>Generating preview...</p>
      </div>
    );
  }

  if (!preview) {
    return (
      <div className="preview-panel empty">
        <p>Select at least 2 personas to preview fusion</p>
      </div>
    );
  }

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <h4>Fusion Preview</h4>
        <div className="compatibility-badge">
          Compatibility: {(preview.compatibilityScore * 100).toFixed(0)}%
        </div>
      </div>

      <div className="preview-traits">
        {Object.entries(preview.estimatedTraits).map(([name, value]) => (
          <TraitBar
            key={name}
            name={name}
            value={value}
            color={value > 0.7 ? '#22c55e' : value < 0.3 ? '#ef4444' : '#3b82f6'}
          />
        ))}
      </div>

      {preview.warnings.length > 0 && (
        <div className="preview-warnings">
          <h5>Warnings</h5>
          <ul>
            {preview.warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// Main Component
export const PersonaFusionLab: React.FC<PersonaFusionLabProps> = ({
  availablePersonas,
  onFusionComplete,
  onPreviewGenerated,
  maxSelectable = 5,
  apiEndpoint = '/api/fusion',
  showAdvancedOptions = true,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [strategy, setStrategy] = useState<FusionStrategy>('weighted_average');
  const [preview, setPreview] = useState<FusionPreview | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isFusing, setIsFusing] = useState(false);
  const [fusionName, setFusionName] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Get selection order for display
  const getSelectionOrder = useCallback(
    (personaId: string) => {
      const idx = selectedIds.indexOf(personaId);
      return idx >= 0 ? idx + 1 : undefined;
    },
    [selectedIds]
  );

  // Toggle persona selection
  const toggleSelection = useCallback(
    (personaId: string) => {
      setSelectedIds((prev) => {
        if (prev.includes(personaId)) {
          return prev.filter((id) => id !== personaId);
        }
        if (prev.length >= maxSelectable) {
          return prev;
        }
        return [...prev, personaId];
      });
      setError(null);
    },
    [maxSelectable]
  );

  // Fetch preview when selection or strategy changes
  useEffect(() => {
    if (selectedIds.length < 2) {
      setPreview(null);
      return;
    }

    const fetchPreview = async () => {
      setIsPreviewLoading(true);
      try {
        const response = await fetch(`${apiEndpoint}/preview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            persona_ids: selectedIds,
            strategy,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to generate preview');
        }

        const data = await response.json();
        setPreview(data);
        onPreviewGenerated?.(data);
      } catch (err) {
        // If API fails, generate local preview
        const localPreview = generateLocalPreview(
          availablePersonas.filter((p) => selectedIds.includes(p.id)),
          strategy
        );
        setPreview(localPreview);
        onPreviewGenerated?.(localPreview);
      } finally {
        setIsPreviewLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchPreview, 300);
    return () => clearTimeout(debounceTimer);
  }, [selectedIds, strategy, apiEndpoint, availablePersonas, onPreviewGenerated]);

  // Generate local preview (fallback)
  const generateLocalPreview = (
    personas: Persona[],
    fusionStrategy: FusionStrategy
  ): FusionPreview => {
    const allTraits: Record<string, number[]> = {};

    personas.forEach((persona) => {
      persona.traits.forEach((trait) => {
        if (!allTraits[trait.name]) {
          allTraits[trait.name] = [];
        }
        allTraits[trait.name].push(trait.value);
      });
    });

    const estimatedTraits: Record<string, number> = {};
    Object.entries(allTraits).forEach(([name, values]) => {
      switch (fusionStrategy) {
        case 'max_pooling':
          estimatedTraits[name] = Math.max(...values);
          break;
        case 'min_pooling':
          estimatedTraits[name] = Math.min(...values);
          break;
        case 'hierarchical':
          estimatedTraits[name] = values[0];
          break;
        case 'consensus':
          const sorted = [...values].sort((a, b) => a - b);
          const mid = Math.floor(sorted.length / 2);
          estimatedTraits[name] =
            sorted.length % 2 === 0
              ? (sorted[mid - 1] + sorted[mid]) / 2
              : sorted[mid];
          break;
        default:
          estimatedTraits[name] =
            values.reduce((a, b) => a + b, 0) / values.length;
      }
    });

    // Calculate compatibility based on variance
    const variances = Object.values(allTraits).map((values) => {
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      return values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    });
    const avgVariance = variances.reduce((a, b) => a + b, 0) / variances.length;
    const compatibilityScore = Math.max(0, 1 - avgVariance * 2);

    return {
      previewId: `preview_${Date.now()}`,
      sourcePersonas: personas.map((p) => p.id),
      estimatedTraits,
      strategy: fusionStrategy,
      compatibilityScore,
      warnings:
        avgVariance > 0.25
          ? ['High variance detected in traits - consider using hierarchical strategy']
          : [],
    };
  };

  // Execute fusion
  const executeFusion = async () => {
    if (selectedIds.length < 2) {
      setError('Select at least 2 personas to fuse');
      return;
    }

    setIsFusing(true);
    setError(null);

    try {
      const response = await fetch(`${apiEndpoint}/fuse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          persona_ids: selectedIds,
          strategy,
          name: fusionName || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Fusion failed');
      }

      const fusedPersona: FusedPersona = await response.json();
      onFusionComplete?.(fusedPersona);

      // Reset state
      setSelectedIds([]);
      setFusionName('');
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fusion failed');
    } finally {
      setIsFusing(false);
    }
  };

  // Selected personas for display
  const selectedPersonas = useMemo(
    () => availablePersonas.filter((p) => selectedIds.includes(p.id)),
    [availablePersonas, selectedIds]
  );

  return (
    <div className="persona-fusion-lab">
      <header className="lab-header">
        <h2>Persona Fusion Lab</h2>
        <p>
          Combine multiple personas to create hybrid agents with blended
          capabilities
        </p>
      </header>

      <div className="lab-content">
        <section className="persona-selection">
          <h3>
            Select Personas ({selectedIds.length}/{maxSelectable})
          </h3>
          <div className="persona-grid">
            {availablePersonas.map((persona) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                isSelected={selectedIds.includes(persona.id)}
                onToggle={() => toggleSelection(persona.id)}
                selectionOrder={getSelectionOrder(persona.id)}
              />
            ))}
          </div>
        </section>

        <aside className="fusion-controls">
          {showAdvancedOptions && (
            <StrategySelector selected={strategy} onChange={setStrategy} />
          )}

          <div className="fusion-name-input">
            <label htmlFor="fusion-name">Fusion Name (optional)</label>
            <input
              id="fusion-name"
              type="text"
              value={fusionName}
              onChange={(e) => setFusionName(e.target.value)}
              placeholder="Enter name for fused persona"
            />
          </div>

          <FusionPreviewPanel preview={preview} isLoading={isPreviewLoading} />

          {error && <div className="error-message">{error}</div>}

          <button
            className="fusion-button"
            onClick={executeFusion}
            disabled={selectedIds.length < 2 || isFusing}
          >
            {isFusing ? 'Fusing...' : 'Create Fusion'}
          </button>

          {selectedPersonas.length > 0 && (
            <div className="selected-summary">
              <h5>Selected for Fusion:</h5>
              <ul>
                {selectedPersonas.map((p, idx) => (
                  <li key={p.id}>
                    {idx + 1}. {p.name}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>

      <style>{`
        .persona-fusion-lab {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
        }

        .lab-header {
          margin-bottom: 32px;
        }

        .lab-header h2 {
          font-size: 28px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 8px 0;
        }

        .lab-header p {
          color: #6b7280;
          margin: 0;
        }

        .lab-content {
          display: grid;
          grid-template-columns: 1fr 360px;
          gap: 32px;
        }

        .persona-selection h3 {
          font-size: 18px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 16px 0;
        }

        .persona-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 16px;
        }

        .persona-card {
          background: white;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
        }

        .persona-card:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }

        .persona-card.selected {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .selection-badge {
          position: absolute;
          top: -8px;
          right: -8px;
          width: 24px;
          height: 24px;
          background: #3b82f6;
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
        }

        .persona-avatar {
          width: 48px;
          height: 48px;
          margin-bottom: 12px;
        }

        .persona-avatar img {
          width: 100%;
          height: 100%;
          border-radius: 50%;
          object-fit: cover;
        }

        .avatar-placeholder {
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 20px;
          font-weight: 600;
        }

        .persona-name {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 4px 0;
        }

        .persona-description {
          font-size: 13px;
          color: #6b7280;
          margin: 0 0 12px 0;
          line-height: 1.4;
        }

        .trait-bar {
          margin-bottom: 8px;
        }

        .trait-bar-label {
          display: flex;
          justify-content: space-between;
          margin-bottom: 4px;
        }

        .trait-name {
          font-size: 12px;
          color: #4b5563;
        }

        .trait-value {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .trait-bar-track {
          height: 6px;
          background: #e5e7eb;
          border-radius: 3px;
          overflow: hidden;
        }

        .trait-bar-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 0.3s ease;
        }

        .more-traits {
          font-size: 12px;
          color: #9ca3af;
        }

        .fusion-controls {
          background: #f9fafb;
          border-radius: 12px;
          padding: 20px;
        }

        .strategy-selector h4 {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 12px 0;
        }

        .strategy-options {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 8px;
        }

        .strategy-option {
          padding: 8px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          background: white;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .strategy-option:hover {
          border-color: #3b82f6;
        }

        .strategy-option.active {
          background: #3b82f6;
          border-color: #3b82f6;
          color: white;
        }

        .strategy-description {
          font-size: 12px;
          color: #6b7280;
          margin: 8px 0 16px 0;
        }

        .fusion-name-input {
          margin-bottom: 16px;
        }

        .fusion-name-input label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #374151;
          margin-bottom: 6px;
        }

        .fusion-name-input input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
        }

        .fusion-name-input input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .preview-panel {
          background: white;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }

        .preview-panel.loading,
        .preview-panel.empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 120px;
          color: #9ca3af;
        }

        .loading-spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .preview-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .preview-header h4 {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          margin: 0;
        }

        .compatibility-badge {
          font-size: 12px;
          padding: 4px 8px;
          background: #ecfdf5;
          color: #059669;
          border-radius: 4px;
          font-weight: 500;
        }

        .preview-warnings {
          margin-top: 12px;
          padding: 12px;
          background: #fffbeb;
          border-radius: 6px;
        }

        .preview-warnings h5 {
          font-size: 12px;
          font-weight: 600;
          color: #92400e;
          margin: 0 0 8px 0;
        }

        .preview-warnings ul {
          margin: 0;
          padding-left: 16px;
        }

        .preview-warnings li {
          font-size: 12px;
          color: #b45309;
        }

        .error-message {
          background: #fef2f2;
          color: #dc2626;
          padding: 12px;
          border-radius: 6px;
          font-size: 13px;
          margin-bottom: 16px;
        }

        .fusion-button {
          width: 100%;
          padding: 14px 20px;
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .fusion-button:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .fusion-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .selected-summary {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #e5e7eb;
        }

        .selected-summary h5 {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 8px 0;
        }

        .selected-summary ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .selected-summary li {
          font-size: 13px;
          color: #6b7280;
          padding: 4px 0;
        }

        @media (max-width: 1024px) {
          .lab-content {
            grid-template-columns: 1fr;
          }

          .fusion-controls {
            order: -1;
          }
        }
      `}</style>
    </div>
  );
};

export default PersonaFusionLab;
