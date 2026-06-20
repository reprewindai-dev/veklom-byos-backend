// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * VEKLOM DISCOVERY — Multi-Chain Deployment Script
 * 
 * Deploy to:
 * - Base Mainnet (8453)
 * - Base Sepolia (84532)
 * - zkSync Era (324)
 * - Unichain (130)
 * - Monad (10143)
 * 
 * Usage:
 * forge script script/VeklomDeploy.s.sol:VeklomDeploy --rpc-url $RPC_URL --account deployer --broadcast
 */

import "forge-std/Script.sol";
import "forge-std/console.sol";

// Mock contracts for reference
interface IVeklomGameRegistry {
    function registerGame(string memory name, string memory ipfsHash) external returns (uint256);
    function registerAgent(string memory name, bool isAutonomous, uint256 initialTrustScore) external returns (uint256);
}

interface IVeklomPaymentVault {
    function receiveX402Payment(address payer, uint256 amount, string memory paymentType) external returns (uint256);
    function batchSettle(uint256[] memory paymentIds, bytes32 merkleRoot) external returns (uint256);
}

interface IVeklomAgentReputation {
    function recordExecution(uint256 agentId, address agentOwner, string memory actionType, bool governanceApproved, bytes32 governanceProofHash, string memory ipfsProofURI) external returns (uint256);
}

interface IVeklomGovernanceGate {
    function evaluateGate(uint256 agentId, uint256 spendAmount, uint256 assetId, uint256 agentTrustScore) external view returns (bool approved, string memory reason);
    function setAgentPolicy(uint256 agentId, string memory policyName) external;
}

contract VeklomDeploy is Script {
    // Network configuration
    struct NetworkConfig {
        uint256 chainId;
        string name;
        address USDC;
        address rpcUrl;
    }

    address constant VEKLOM_OWNER = 0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d;
    
    mapping(uint256 => NetworkConfig) public networks;
    
    struct DeploymentResult {
        uint256 chainId;
        string chainName;
        address gameRegistry;
        address paymentVault;
        address agentReputation;
        address governanceGate;
        uint256 deploymentTime;
    }

    DeploymentResult[] public deployments;

    function setUp() public {
        // Base Mainnet
        networks[8453] = NetworkConfig({
            chainId: 8453,
            name: "Base Mainnet",
            USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b3228cdeC9F,
            rpcUrl: vm.envAddress("BASE_MAINNET_RPC")
        });

        // Base Sepolia Testnet
        networks[84532] = NetworkConfig({
            chainId: 84532,
            name: "Base Sepolia",
            USDC: 0x0000000000000000000000000000000000000000, // Mock for testnet
            rpcUrl: vm.envAddress("BASE_SEPOLIA_RPC")
        });

        // zkSync Era
        networks[324] = NetworkConfig({
            chainId: 324,
            name: "zkSync Era",
            USDC: 0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4,
            rpcUrl: vm.envAddress("ZKSYNC_RPC")
        });

        // Unichain
        networks[130] = NetworkConfig({
            chainId: 130,
            name: "Unichain",
            USDC: 0x0000000000000000000000000000000000000000, // To be determined
            rpcUrl: vm.envAddress("UNICHAIN_RPC")
        });

        // Monad
        networks[10143] = NetworkConfig({
            chainId: 10143,
            name: "Monad",
            USDC: 0x0000000000000000000000000000000000000000, // To be determined
            rpcUrl: vm.envAddress("MONAD_RPC")
        });
    }

    function run() public {
        // Get chain ID to deploy for
        uint256 chainId = block.chainid;
        
        vm.startBroadcast(vm.envUint("PRIVATE_KEY"));

        // Deploy to current chain
        deployToChain(chainId);

        vm.stopBroadcast();

        // Print results
        console.log("\n=== VEKLOM DISCOVERY DEPLOYMENT ===\n");
        for (uint256 i = 0; i < deployments.length; i++) {
            printDeploymentResult(deployments[i]);
        }
    }

    function deployToChain(uint256 chainId) internal {
        NetworkConfig memory config = networks[chainId];
        require(config.chainId != 0, "Unsupported chain");

        console.log("Deploying to:", config.name);

        // 1. Deploy VeklomGameRegistry
        bytes memory registryCode = type(VeklomGameRegistryProxy).creationCode;
        address gameRegistry = deploy("VeklomGameRegistry", registryCode);

        // 2. Deploy VeklomPaymentVault
        bytes memory vaultCode = abi.encodePacked(
            type(VeklomPaymentVaultProxy).creationCode,
            abi.encode(config.USDC)
        );
        address paymentVault = deploy("VeklomPaymentVault", vaultCode);

        // 3. Deploy VeklomAgentReputation
        bytes memory reputationCode = type(VeklomAgentReputationProxy).creationCode;
        address agentReputation = deploy("VeklomAgentReputation", reputationCode);

        // 4. Deploy VeklomGovernanceGate
        bytes memory governanceCode = type(VeklomGovernanceGateProxy).creationCode;
        address governanceGate = deploy("VeklomGovernanceGate", governanceCode);

        // Record deployment
        DeploymentResult memory result = DeploymentResult({
            chainId: chainId,
            chainName: config.name,
            gameRegistry: gameRegistry,
            paymentVault: paymentVault,
            agentReputation: agentReputation,
            governanceGate: governanceGate,
            deploymentTime: block.timestamp
        });

        deployments.push(result);

        // Initialize contracts
        initializeContracts(gameRegistry, paymentVault, agentReputation, governanceGate);

        console.log("Deployment complete for:", config.name);
    }

    function initializeContracts(
        address gameRegistry,
        address paymentVault,
        address agentReputation,
        address governanceGate
    ) internal {
        // Set contract ownership to VEKLOM_OWNER
        // This would call the actual contract initialization functions

        // Verify initial state
        console.log("GameRegistry deployed at:", gameRegistry);
        console.log("PaymentVault deployed at:", paymentVault);
        console.log("AgentReputation deployed at:", agentReputation);
        console.log("GovernanceGate deployed at:", governanceGate);
    }

    function deploy(string memory contractName, bytes memory code) internal returns (address) {
        address deployed;
        assembly {
            deployed := create(0, add(code, 0x20), mload(code))
            if iszero(deployed) {
                revert(0, 0)
            }
        }
        console.log(contractName, "deployed at:", deployed);
        return deployed;
    }

    function printDeploymentResult(DeploymentResult memory result) internal view {
        console.log("=== Deployment to", result.chainName, "===");
        console.log("Chain ID:", result.chainId);
        console.log("GameRegistry:", result.gameRegistry);
        console.log("PaymentVault:", result.paymentVault);
        console.log("AgentReputation:", result.agentReputation);
        console.log("GovernanceGate:", result.governanceGate);
        console.log("Deployed at:", result.deploymentTime);
        console.log("");
    }
}

// ============ PROXY CONTRACTS FOR REFERENCE ============

contract VeklomGameRegistryProxy {
    // Placeholder - actual implementation in contracts
}

contract VeklomPaymentVaultProxy {
    // Placeholder - actual implementation in contracts
}

contract VeklomAgentReputationProxy {
    // Placeholder - actual implementation in contracts
}

contract VeklomGovernanceGateProxy {
    // Placeholder - actual implementation in contracts
}

/**
 * DEPLOYMENT INSTRUCTIONS
 * 
 * 1. Set environment variables:
 *    export PRIVATE_KEY=<your-private-key>
 *    export BASE_MAINNET_RPC=https://mainnet.base.org
 *    export BASE_SEPOLIA_RPC=https://sepolia.base.org
 *    export ZKSYNC_RPC=https://mainnet.era.zksync.io
 *    export UNICHAIN_RPC=https://rpc.unichain.org
 *    export MONAD_RPC=https://rpc.monad.xyz
 * 
 * 2. Deploy to Base Mainnet:
 *    forge script script/VeklomDeploy.s.sol:VeklomDeploy \
 *      --rpc-url $BASE_MAINNET_RPC \
 *      --account deployer \
 *      --broadcast
 * 
 * 3. Deploy to Base Sepolia:
 *    forge script script/VeklomDeploy.s.sol:VeklomDeploy \
 *      --rpc-url $BASE_SEPOLIA_RPC \
 *      --account deployer \
 *      --broadcast
 * 
 * 4. Deploy to all networks at once:
 *    for CHAIN in base zksync unichain monad; do
 *      RPC=$(eval echo \$${CHAIN}_RPC)
 *      forge script script/VeklomDeploy.s.sol:VeklomDeploy \
 *        --rpc-url $RPC \
 *        --account deployer \
 *        --broadcast
 *    done
 * 
 * After deployment:
 * - Verify contracts on block explorers
 * - Save deployed addresses to config/.env.$CHAIN
 * - Initialize contracts with governance rules
 * - Register initial agents and games
 */
