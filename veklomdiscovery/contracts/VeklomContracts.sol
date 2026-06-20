// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * VEKLOM DISCOVERY — On-Chain Game Infrastructure
 * 
 * Contracts:
 * 1. VeklomGameRegistry - Game & agent metadata
 * 2. VeklomPaymentVault - X402 payment settlement + USDC drops
 * 3. VeklomAgentReputation - Governance proof ledger + trust scores
 * 4. VeklomGovernanceGate - Policy enforcement for autonomous agents
 */

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

// ============ VEKLOM GAME REGISTRY ============
contract VeklomGameRegistry is Ownable, ReentrancyGuard {
    using ECDSA for bytes32;

    struct Game {
        uint256 id;
        string name;
        address owner;
        string ipfsHash;
        uint256 createdAt;
        bool active;
        uint256 totalPlayers;
    }

    struct Agent {
        uint256 id;
        address owner;
        string name;
        uint256 trustScore;
        uint256 level;
        bool isAutonomous;
        uint256 createdAt;
    }

    mapping(uint256 => Game) public games;
    mapping(uint256 => Agent) public agents;
    mapping(address => uint256[]) public userGames;
    mapping(address => uint256[]) public userAgents;
    
    uint256 public gameCounter;
    uint256 public agentCounter;
    
    address public veklomAddress = 0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d;
    address public baseName = 0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d; // veklom.base.eth

    event GameRegistered(uint256 indexed gameId, address indexed owner, string name);
    event AgentRegistered(uint256 indexed agentId, address indexed owner, string name, bool isAutonomous);
    event TrustScoreUpdated(uint256 indexed agentId, uint256 newScore);

    /**
     * Register a new game on Veklom
     */
    function registerGame(string memory name, string memory ipfsHash) external nonReentrant returns (uint256) {
        require(bytes(name).length > 0, "Game name required");
        require(bytes(ipfsHash).length > 0, "IPFS hash required");

        uint256 gameId = ++gameCounter;
        
        games[gameId] = Game({
            id: gameId,
            name: name,
            owner: msg.sender,
            ipfsHash: ipfsHash,
            createdAt: block.timestamp,
            active: true,
            totalPlayers: 0
        });

        userGames[msg.sender].push(gameId);

        emit GameRegistered(gameId, msg.sender, name);
        return gameId;
    }

    /**
     * Register an autonomous agent with initial trust score
     */
    function registerAgent(
        string memory name,
        bool isAutonomous,
        uint256 initialTrustScore
    ) external nonReentrant returns (uint256) {
        require(bytes(name).length > 0, "Agent name required");
        require(initialTrustScore >= 100 && initialTrustScore <= 1000, "Trust score range: 100-1000");

        uint256 agentId = ++agentCounter;
        
        agents[agentId] = Agent({
            id: agentId,
            owner: msg.sender,
            name: name,
            trustScore: initialTrustScore,
            level: 1,
            isAutonomous: isAutonomous,
            createdAt: block.timestamp
        });

        userAgents[msg.sender].push(agentId);

        emit AgentRegistered(agentId, msg.sender, name, isAutonomous);
        return agentId;
    }

    /**
     * Update agent trust score (callable only by governance)
     */
    function updateAgentTrustScore(uint256 agentId, uint256 newScore) external onlyOwner {
        require(agentId > 0 && agentId <= agentCounter, "Invalid agent ID");
        require(newScore >= 100 && newScore <= 1000, "Trust score range: 100-1000");
        
        agents[agentId].trustScore = newScore;
        emit TrustScoreUpdated(agentId, newScore);
    }

    /**
     * Get all games owned by an address
     */
    function getUserGames(address user) external view returns (uint256[] memory) {
        return userGames[user];
    }

    /**
     * Get all agents owned by an address
     */
    function getUserAgents(address user) external view returns (uint256[] memory) {
        return userAgents[user];
    }
}

// ============ VEKLOM PAYMENT VAULT ============
contract VeklomPaymentVault is Ownable, ReentrancyGuard {
    IERC20 public immutable USDC;
    
    address public veklomAddress = 0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d;
    uint256 public totalVolumeProcessed;
    uint256 public totalPaymentsReceived;

    struct Payment {
        uint256 id;
        address payer;
        uint256 amount;
        string paymentType; // "x402", "mission_claim", "race_entry"
        uint256 timestamp;
        bool settled;
        string proofHash;
    }

    struct Batch {
        uint256 id;
        uint256[] paymentIds;
        uint256 totalAmount;
        uint256 createdAt;
        bool settled;
        bytes32 merkleRoot;
    }

    mapping(uint256 => Payment) public payments;
    mapping(uint256 => Batch) public batches;
    mapping(address => uint256[]) public userPayments;
    mapping(address => uint256) public userBalance;

    uint256 public paymentCounter;
    uint256 public batchCounter;

    event X402PaymentReceived(uint256 indexed paymentId, address indexed payer, uint256 amount);
    event BatchSettled(uint256 indexed batchId, uint256 totalAmount, bytes32 merkleRoot);
    event BalanceUpdated(address indexed user, uint256 newBalance);

    /**
     * Initialize with USDC token address
     * Base Mainnet USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F
     */
    constructor(address usdcAddress) {
        USDC = IERC20(usdcAddress);
    }

    /**
     * Receive X402 payment (called after user approves via Base MCP)
     */
    function receiveX402Payment(
        address payer,
        uint256 amount,
        string memory paymentType
    ) external nonReentrant returns (uint256) {
        require(amount > 0, "Amount must be > 0");
        require(msg.sender == veklomAddress || msg.sender == owner(), "Only Veklom can receive payments");

        uint256 paymentId = ++paymentCounter;

        // Record payment
        payments[paymentId] = Payment({
            id: paymentId,
            payer: payer,
            amount: amount,
            paymentType: paymentType,
            timestamp: block.timestamp,
            settled: false,
            proofHash: ""
        });

        userPayments[payer].push(paymentId);
        userBalance[payer] += amount;
        totalPaymentsReceived += amount;

        emit X402PaymentReceived(paymentId, payer, amount);
        emit BalanceUpdated(payer, userBalance[payer]);

        return paymentId;
    }

    /**
     * Batch settle multiple payments (merkle tree proof)
     * Happens periodically to reduce on-chain overhead
     */
    function batchSettle(
        uint256[] memory paymentIds,
        bytes32 merkleRoot
    ) external onlyOwner nonReentrant returns (uint256) {
        require(paymentIds.length > 0, "Batch must contain payments");

        uint256 batchId = ++batchCounter;
        uint256 batchTotal = 0;

        for (uint256 i = 0; i < paymentIds.length; i++) {
            require(!payments[paymentIds[i]].settled, "Payment already settled");
            batchTotal += payments[paymentIds[i]].amount;
            payments[paymentIds[i]].settled = true;
        }

        batches[batchId] = Batch({
            id: batchId,
            paymentIds: paymentIds,
            totalAmount: batchTotal,
            createdAt: block.timestamp,
            settled: true,
            merkleRoot: merkleRoot
        });

        totalVolumeProcessed += batchTotal;

        emit BatchSettled(batchId, batchTotal, merkleRoot);
        return batchId;
    }

    /**
     * Claim user balance (withdraw earned USDC)
     */
    function claimBalance() external nonReentrant {
        uint256 balance = userBalance[msg.sender];
        require(balance > 0, "No balance to claim");

        userBalance[msg.sender] = 0;

        require(USDC.transfer(msg.sender, balance), "Transfer failed");
        emit BalanceUpdated(msg.sender, 0);
    }
}

// ============ VEKLOM AGENT REPUTATION ============
contract VeklomAgentReputation is Ownable {
    struct ExecutionProof {
        uint256 id;
        uint256 agentId;
        address agentOwner;
        string actionType; // "race", "mission", "policy_update"
        uint256 timestamp;
        bool governanceApproved;
        bytes32 governanceProofHash;
        string ipfsProofURI;
    }

    struct GovernanceGate {
        string gateName;
        bool passed;
        uint256 evaluatedAt;
        bytes32 proofHash;
    }

    mapping(uint256 => ExecutionProof) public proofs;
    mapping(uint256 => GovernanceGate[]) public executionGates;
    mapping(uint256 => uint256[]) public agentExecutionHistory;

    uint256 public proofCounter;

    event ExecutionProofRecorded(uint256 indexed proofId, uint256 indexed agentId, string actionType);
    event GovernanceGatesEvaluated(uint256 indexed proofId, uint256 gatesPassed, uint256 totalGates);

    /**
     * Record an executed action with governance proof
     */
    function recordExecution(
        uint256 agentId,
        address agentOwner,
        string memory actionType,
        bool governanceApproved,
        bytes32 governanceProofHash,
        string memory ipfsProofURI
    ) external onlyOwner returns (uint256) {
        uint256 proofId = ++proofCounter;

        proofs[proofId] = ExecutionProof({
            id: proofId,
            agentId: agentId,
            agentOwner: agentOwner,
            actionType: actionType,
            timestamp: block.timestamp,
            governanceApproved: governanceApproved,
            governanceProofHash: governanceProofHash,
            ipfsProofURI: ipfsProofURI
        });

        agentExecutionHistory[agentId].push(proofId);

        emit ExecutionProofRecorded(proofId, agentId, actionType);
        return proofId;
    }

    /**
     * Record governance gate evaluation results
     */
    function recordGovernanceGates(
        uint256 proofId,
        string[] memory gateNames,
        bool[] memory results
    ) external onlyOwner {
        require(gateNames.length == results.length, "Length mismatch");
        
        uint256 passed = 0;
        for (uint256 i = 0; i < results.length; i++) {
            if (results[i]) passed++;
            
            executionGates[proofId].push(GovernanceGate({
                gateName: gateNames[i],
                passed: results[i],
                evaluatedAt: block.timestamp,
                proofHash: keccak256(abi.encode(gateNames[i], results[i]))
            }));
        }

        emit GovernanceGatesEvaluated(proofId, passed, gateNames.length);
    }

    /**
     * Get full execution history for agent
     */
    function getAgentExecutionHistory(uint256 agentId, uint256 limit) external view returns (uint256[] memory) {
        uint256[] storage history = agentExecutionHistory[agentId];
        uint256 start = history.length > limit ? history.length - limit : 0;
        
        uint256[] memory result = new uint256[](history.length - start);
        for (uint256 i = 0; i < result.length; i++) {
            result[i] = history[start + i];
        }
        return result;
    }

    /**
     * Verify governance proof on-chain
     */
    function verifyGovernanceProof(uint256 proofId) external view returns (bool, uint256) {
        ExecutionProof memory proof = proofs[proofId];
        GovernanceGate[] memory gates = executionGates[proofId];
        
        uint256 passedGates = 0;
        for (uint256 i = 0; i < gates.length; i++) {
            if (gates[i].passed) passedGates++;
        }

        bool approved = passedGates == gates.length && proof.governanceApproved;
        return (approved, passedGates);
    }
}

// ============ VEKLOM GOVERNANCE GATE ============
contract VeklomGovernanceGate is Ownable {
    struct Policy {
        string name;
        uint256 maxSpendPerTx;
        bool requiresApproval;
        uint256[] allowedAssets;
    }

    mapping(string => Policy) public policies;
    mapping(uint256 => string) public agentPolicy; // agentId -> policyName

    event PolicyDefined(string indexed policyName, uint256 maxSpend);
    event AgentPolicySet(uint256 indexed agentId, string policyName);

    constructor() {
        // Define default policies
        uint256[] memory conservative = new uint256[](2);
        conservative[0] = 1; // USDC
        conservative[1] = 2; // WETH
        
        policies["conservative"] = Policy({
            name: "conservative",
            maxSpendPerTx: 10,
            requiresApproval: true,
            allowedAssets: conservative
        });

        uint256[] memory balanced = new uint256[](3);
        balanced[0] = 1;
        balanced[1] = 2;
        balanced[2] = 0;
        
        policies["balanced"] = Policy({
            name: "balanced",
            maxSpendPerTx: 50,
            requiresApproval: false,
            allowedAssets: balanced
        });

        uint256[] memory aggressive = new uint256[](4);
        aggressive[0] = 1;
        aggressive[1] = 2;
        aggressive[2] = 0;
        aggressive[3] = 3;
        
        policies["aggressive"] = Policy({
            name: "aggressive",
            maxSpendPerTx: 500,
            requiresApproval: false,
            allowedAssets: aggressive
        });
    }

    /**
     * Evaluate if action passes governance gate
     */
    function evaluateGate(
        uint256 agentId,
        uint256 spendAmount,
        uint256 assetId,
        uint256 agentTrustScore
    ) external view returns (bool approved, string memory reason) {
        string memory policyName = agentPolicy[agentId];
        if (bytes(policyName).length == 0) {
            return (false, "Agent policy not set");
        }

        Policy memory policy = policies[policyName];

        // Check spend limit
        if (spendAmount > policy.maxSpendPerTx) {
            return (false, "Exceeds spend limit");
        }

        // Check asset allowlist
        bool assetAllowed = false;
        for (uint256 i = 0; i < policy.allowedAssets.length; i++) {
            if (policy.allowedAssets[i] == assetId) {
                assetAllowed = true;
                break;
            }
        }
        if (!assetAllowed) {
            return (false, "Asset not allowed");
        }

        // Check trust score minimum
        if (agentTrustScore < 400) {
            return (false, "Insufficient trust score");
        }

        return (true, "All gates passed");
    }

    /**
     * Set policy for an agent
     */
    function setAgentPolicy(uint256 agentId, string memory policyName) external onlyOwner {
        require(bytes(policies[policyName].name).length > 0, "Policy not defined");
        agentPolicy[agentId] = policyName;
        emit AgentPolicySet(agentId, policyName);
    }
}
