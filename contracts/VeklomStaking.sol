// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract VeklomStaking {
    IERC20 public immutable stakingToken;
    address public orchestrator;
    
    // Mapping of provider ID (string) to total staked amount
    mapping(string => uint256) public providerBonds;
    
    event BondDeposited(string indexed providerId, address depositor, uint256 amount);
    event BondSlashed(string indexed providerId, uint256 penaltyAmount, uint256 newBalance);
    event OrchestratorUpdated(address oldOrchestrator, address newOrchestrator);

    modifier onlyOrchestrator() {
        require(msg.sender == orchestrator, "VeklomStaking: caller is not the orchestrator");
        _;
    }

    constructor(address _stakingToken) {
        stakingToken = IERC20(_stakingToken);
        orchestrator = msg.sender; // Initial deployer is the orchestrator
    }

    function updateOrchestrator(address _newOrchestrator) external onlyOrchestrator {
        require(_newOrchestrator != address(0), "VeklomStaking: orchestrator cannot be zero address");
        emit OrchestratorUpdated(orchestrator, _newOrchestrator);
        orchestrator = _newOrchestrator;
    }

    // Provider (or anyone) can deposit stake on behalf of a specific API/Provider ID
    function depositBond(string calldata providerId, uint256 amount) external {
        require(amount > 0, "VeklomStaking: amount must be greater than 0");
        
        // Transfer tokens from sender to this contract
        require(stakingToken.transferFrom(msg.sender, address(this), amount), "VeklomStaking: transfer failed");
        
        providerBonds[providerId] += amount;
        
        emit BondDeposited(providerId, msg.sender, amount);
    }

    // Only the backend orchestrator can slash bonds based on off-chain KDE consensus logic
    function slashBond(string calldata providerId, uint256 penaltyAmount) external onlyOrchestrator {
        uint256 currentBond = providerBonds[providerId];
        require(currentBond > 0, "VeklomStaking: no bond to slash");
        
        // Cannot slash more than the current bond
        uint256 actualPenalty = penaltyAmount > currentBond ? currentBond : penaltyAmount;
        
        providerBonds[providerId] -= actualPenalty;
        
        // In a real implementation, the penalty would be sent to a treasury or distributed to verifiers
        // For this V1, we simply burn/lock it in the contract by deducting it from the provider's balance
        // We could also explicitly burn it if the token supports it, or send to orchestrator:
        // stakingToken.transfer(orchestrator, actualPenalty);
        
        emit BondSlashed(providerId, actualPenalty, providerBonds[providerId]);
    }
    
    function getBond(string calldata providerId) external view returns (uint256) {
        return providerBonds[providerId];
    }
}
