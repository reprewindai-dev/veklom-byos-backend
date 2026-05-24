<?php

require __DIR__.'/vendor/autoload.php';
$app = require_once __DIR__.'/bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

$deployment = \App\Models\ApplicationDeploymentQueue::find(817);
echo "Status: " . $deployment->status . "\n";
echo "Logs: \n" . $deployment->logs . "\n";
