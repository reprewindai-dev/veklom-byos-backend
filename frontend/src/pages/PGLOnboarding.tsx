import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { 
  Shield, 
  User, 
  Key, 
  CheckCircle, 
  AlertCircle, 
  ArrowRight, 
  Loader,
  Database,
  GitBranch,
  Wallet,
  FileText
} from 'lucide-react';

interface PGLProfile {
  operator_name?: string;
  operator_identity: string;
  workspace_authority_id: string;
  agent_certificate_id: string;
  genome_hash: string;
  ledger_root: string;
  lineage_root: string;
  wallet_binding?: string;
  status: 'pending' | 'active' | 'verified';
}

export const PGLOnboarding: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [pglProfile, setPGLProfile] = useState<Partial<PGLProfile>>({});
  
  const steps = [
    { title: 'Operator Identity', icon: User, description: 'Create your operator identity' },
    { title: 'Workspace Authority', icon: Shield, description: 'Configure workspace authority profile' },
    { title: 'Agent Certificate', icon: Key, description: 'Generate first agent certificate' },
    { title: 'Genome Preview', icon: Database, description: 'Review agent genome configuration' },
    { title: 'Ledger & Lineage', icon: GitBranch, description: 'Initialize ledger and lineage roots' },
    { title: 'Wallet Binding', icon: Wallet, description: 'Optional wallet connection for payments' },
    { title: 'First Proof', icon: FileText, description: 'Generate first harmless proof' }
  ];

  useEffect(() => {
    // Check if user already has PGL profile
    checkExistingPGL();
  }, []);

  const checkExistingPGL = async () => {
    try {
      const response = await api('/pgl/profile');
      if (response && response.status !== 'pending') {
        // User already has PGL, redirect to home
        navigate('/home');
      }
    } catch (err) {
      // No PGL exists, continue with onboarding
    }
  };

  const createOperatorIdentity = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api('/pgl/onboarding/operator-identity', {
        method: 'POST',
        body: JSON.stringify({
          operator_name: pglProfile.operator_name || 'Primary Operator',
          jurisdiction: 'US',
          declared_purpose: 'AI Agent Management'
        })
      });
      
      setPGLProfile((prev: Partial<PGLProfile>) => ({
        ...prev,
        operator_identity: response.operator_identity_id,
        workspace_authority_id: response.workspace_authority_id
      }));
      
      setCurrentStep(1);
    } catch (err: any) {
      setError(err.message || 'Failed to create operator identity');
    } finally {
      setIsLoading(false);
    }
  };

  const createWorkspaceAuthority = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api('/pgl/onboarding/workspace-authority', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: pglProfile.workspace_authority_id,
          authority_level: 'operator',
          permissions: ['agent_management', 'policy_enforcement', 'execution_control']
        })
      });
      
      setPGLProfile((prev: Partial<PGLProfile>) => ({
        ...prev,
        workspace_authority_id: response.workspace_authority_id
      }));
      
      setCurrentStep(2);
    } catch (err: any) {
      setError(err.message || 'Failed to create workspace authority');
    } finally {
      setIsLoading(false);
    }
  };

  const generateAgentCertificate = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api('/pgl/onboarding/agent-certificate', {
        method: 'POST',
        body: JSON.stringify({
          agent_name: 'Primary Agent',
          agent_type: 'autonomous',
          capabilities: ['web_search', 'data_analysis', 'automation'],
          safety_rules: ['no_external_payments', 'data_privacy', 'scope_enforcement']
        })
      });
      
      setPGLProfile((prev: Partial<PGLProfile>) => ({
        ...prev,
        agent_certificate_id: response.certificate_id,
        genome_hash: response.genome_hash
      }));
      
      setCurrentStep(3);
    } catch (err: any) {
      setError(err.message || 'Failed to generate agent certificate');
    } finally {
      setIsLoading(false);
    }
  };

  const initializeLedgerLineage = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api('/pgl/onboarding/ledger-lineage', {
        method: 'POST',
        body: JSON.stringify({
          certificate_id: pglProfile.agent_certificate_id,
          genesis_block: {
            timestamp: new Date().toISOString(),
            operator: pglProfile.operator_identity,
            workspace: pglProfile.workspace_authority_id
          }
        })
      });
      
      setPGLProfile((prev: Partial<PGLProfile>) => ({
        ...prev,
        ledger_root: response.ledger_root,
        lineage_root: response.lineage_root
      }));
      
      setCurrentStep(5); // Skip wallet binding for now
    } catch (err: any) {
      setError(err.message || 'Failed to initialize ledger and lineage');
    } finally {
      setIsLoading(false);
    }
  };

  const generateFirstProof = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api('/pgl/onboarding/first-proof', {
        method: 'POST',
        body: JSON.stringify({
          certificate_id: pglProfile.agent_certificate_id,
          proof_type: 'identity_verification',
          payload: {
            action: 'system_check',
            scope: 'readonly',
            timestamp: new Date().toISOString()
          }
        })
      });
      
      setPGLProfile((prev: Partial<PGLProfile>) => ({
        ...prev,
        status: 'verified'
      }));
      
      // Unlock workspace and redirect to home
      await api('/pgl/onboarding/complete', {
        method: 'POST',
        body: JSON.stringify({
          profile_id: response.profile_id
        })
      });
      
      navigate('/home');
    } catch (err: any) {
      setError(err.message || 'Failed to generate first proof');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepAction = () => {
    switch (currentStep) {
      case 0:
        createOperatorIdentity();
        break;
      case 1:
        createWorkspaceAuthority();
        break;
      case 2:
        generateAgentCertificate();
        break;
      case 3:
        setCurrentStep(4);
        break;
      case 4:
        initializeLedgerLineage();
        break;
      case 5:
        setCurrentStep(6);
        break;
      case 6:
        generateFirstProof();
        break;
      default:
        break;
    }
  };

  const renderStepContent = () => {
    const step = steps[currentStep];
    
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Create Operator Identity</h3>
            <p className="text-sm text-gray-400">
              Your operator identity is the foundation of your authority in the Veklom system.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <User size={16} className="text-blue-400" />
                <span className="text-sm font-medium">Operator Identity Features:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Cryptographic identity binding</li>
                <li>• Jurisdiction and purpose declaration</li>
                <li>• Workspace authority anchoring</li>
                <li>• Audit trail integration</li>
              </ul>
            </div>
          </div>
        );
      
      case 1:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Workspace Authority Profile</h3>
            <p className="text-sm text-gray-400">
              Configure your workspace authority to manage agents and enforce policies.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Shield size={16} className="text-green-400" />
                <span className="text-sm font-medium">Authority Permissions:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Agent lifecycle management</li>
                <li>• Policy enforcement controls</li>
                <li>• Execution scope boundaries</li>
                <li>• Resource allocation limits</li>
              </ul>
            </div>
          </div>
        );
      
      case 2:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Generate Agent Certificate</h3>
            <p className="text-sm text-gray-400">
              Create your first agent certificate with defined capabilities and safety rules.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Key size={16} className="text-yellow-400" />
                <span className="text-sm font-medium">Certificate Includes:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Agent capabilities and tools</li>
                <li>• Safety rule definitions</li>
                <li>• Genome hash fingerprint</li>
                <li>• Scope enforcement parameters</li>
              </ul>
            </div>
          </div>
        );
      
      case 3:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Genome Preview</h3>
            <p className="text-sm text-gray-400">
              Review your agent's genome configuration before finalizing.
            </p>
            {pglProfile.genome_hash && (
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Database size={16} className="text-purple-400" />
                  <span className="text-sm font-medium">Genome Hash:</span>
                </div>
                <code className="text-xs text-green-400 break-all">
                  {pglProfile.genome_hash}
                </code>
              </div>
            )}
          </div>
        );
      
      case 4:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Ledger & Lineage Roots</h3>
            <p className="text-sm text-gray-400">
              Initialize the immutable ledger and lineage tracking systems.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <GitBranch size={16} className="text-cyan-400" />
                <span className="text-sm font-medium">Root Systems:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Immutable audit ledger</li>
                <li>• Agent lineage tracking</li>
                <li>• Decision provenance</li>
                <li>• Compliance verification</li>
              </ul>
            </div>
          </div>
        );
      
      case 5:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Wallet Binding (Optional)</h3>
            <p className="text-sm text-gray-400">
              Connect a wallet for payment-enabled operations. This can be done later.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Wallet size={16} className="text-orange-400" />
                <span className="text-sm font-medium">Payment Features:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• x402 payment integration</li>
                <li>• Budget enforcement</li>
                <li>• Cost tracking</li>
                <li>• Vendor payments</li>
              </ul>
            </div>
          </div>
        );
      
      case 6:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Generate First Proof</h3>
            <p className="text-sm text-gray-400">
              Create your first proof to verify the system is working correctly.
            </p>
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText size={16} className="text-emerald-400" />
                <span className="text-sm font-medium">Proof Verification:</span>
              </div>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Identity verification</li>
                <li>• System health check</li>
                <li>• Policy enforcement test</li>
                <li>• Audit trail validation</li>
              </ul>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
      <div className="max-w-4xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Shield className="text-orange-500" size={32} />
            <h1 className="text-3xl font-bold">PGL Onboarding</h1>
          </div>
          <p className="text-gray-400">
            Project Governance Layer - Establish your authority foundation
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={index} className="flex items-center">
                <div className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                  ${index < currentStep ? 'bg-green-500 text-white' : 
                    index === currentStep ? 'bg-orange-500 text-white' : 
                    'bg-neutral-800 text-gray-400'}
                `}>
                  {index < currentStep ? (
                    <CheckCircle size={16} />
                  ) : (
                    <step.icon size={16} />
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div className={`
                    w-full h-0.5 mx-2
                    ${index < currentStep ? 'bg-green-500' : 'bg-neutral-800'}
                  `} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2">
            {steps.map((step, index) => (
              <div key={index} className="text-xs text-gray-400 text-center" style={{ width: `${100 / steps.length}%` }}>
                {step.title}
              </div>
            ))}
          </div>
        </div>

        {/* Current Step Content */}
        <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-8 mb-6">
          {renderStepContent()}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 flex items-center gap-3">
            <AlertCircle size={16} className="text-red-400" />
            <span className="text-sm text-red-400">{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0 || isLoading}
            className="px-6 py-2 bg-neutral-800 text-white rounded-lg hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          
          <button
            onClick={handleStepAction}
            disabled={isLoading}
            className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader size={16} className="animate-spin" />
                Processing...
              </>
            ) : (
              <>
                {currentStep === steps.length - 1 ? 'Complete Setup' : 'Continue'}
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
