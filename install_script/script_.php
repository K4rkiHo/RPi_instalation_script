<?php
// příjem dat z GW1000
$weather_data = $_POST;

// ID nebo název meteostanice
$meteostation_id = 'meteostation1';

$user = 'pi';
$pass = '%PASS%';
$db = 'Ecowitt_database';

$conn = new mysqli('localhost', $user, $pass, $db);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
} else { 
    echo "Connect</br>";
}

// Zkontroluje, zda existuje tabulka pro meteostanici, pokud ne, vytvoří ji.
$table_name = 'Weather_table_' . $meteostation_id;
$sql_create_table = "CREATE TABLE IF NOT EXISTS $table_name (
    id INT AUTO_INCREMENT PRIMARY KEY,
    time DATETIME";
$conn->query($sql_create_table);

// Definice pole senzorů a jim odpovídajících klíčů (názvů) pro každou meteostanici
$sensors = array(
    'indoor_temperature_F' => 'tempinf',
    'indoor_humidity_percent' => 'humidityin',
    'pressure_relative_inHg' => 'baromrelin',
    'pressure_absolute_inHg' => 'baromabsin',
    'outdoor_temperature_F' => 'tempf',
    'outdoor_humidity_percent' => 'humidity',
    'wind_angle' => 'winddir',
    'wind_speed_mph' => 'windspeedmph',
    'wind_gust_mph' => 'windgustmph',
    'wind_gust_max_mph' => 'maxdailygust',
    'solar_radiation_Wm2' => 'solarradiation',
    'solar_uv' => 'uv',
    'rain_rate_inhr' => 'rainratein',
    'rain_event_in' => 'eventrainin',
    'rain_hourly_in' => 'hourlyrainin',
    'rain_weekly_in' => 'weeklyrainin',
    'rain_yearly_in' => 'yearlyrainin',
    'rain_total_in' => 'totalrainin',
);

// Přidání senzorů, které jsou ve vstupních datech, do pole sensors
foreach ($weather_data as $key => $value) {
    if (!array_key_exists($key, $sensors)) {
        $sensors[$key] = $key;
    }
}

// Přidání každého senzoru do schématu tabulky
$sql_create_table .= ",";
foreach ($sensors as $column_name => $sensor_key) {
    $sql_create_table .= "\n $column_name DECIMAL(5,2),";
}
$sql_create_table = rtrim($sql_create_table, ",") . "\n)";

$conn->query($sql_create_table);

// Zkontrolujte, zda meteostanice existuje v databázi, pokud ne, vytvořte novou položku.
$sql_check_meteostation = "SELECT id FROM Meteostations WHERE meteostation_id = ?";
$stmt = $conn->prepare($sql_check_meteostation);
$stmt->bind_param("s", $meteostation_id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows === 0) {
    // Meteostanice neexistuje, vytvořte novou položku v tabulce Meteostanice
    $sql_insert_meteostation = "INSERT INTO Meteostations (meteostation_id) VALUES (?)";
    $stmt = $conn->prepare($sql_insert_meteostation);
    $stmt->bind_param("s", $meteostation_id);
    if ($stmt->execute()) {
        // Získat ID nově vložené meteostanice
        $meteostation_id = $conn->insert_id;
    } else {
        die("Error creating meteostation entry: " . $conn->error);
    }
}

// Aktuální čas
$time = date('Y-m-d H:i:s');

// Nahrazení prázdné hodnoty pro temp1f jinou hodnotou, pokud je prázdná
if (empty($weather_data['temp1f'])) {
    $weather_data['temp1f'] = 2; // Můžete změnit na jakoukoliv jinou hodnotu podle potřeby
}

// Kontrola a případná náhrada hodnot
foreach (array('temp1f', 'humidity1', 'wh65batt', 'batt1') as $key) {
    if (!isset($weather_data[$key]) || !is_numeric($weather_data[$key]) || $weather_data[$key] != 1) {
        if (isset($weather_data[$sensors[$key]])) {
            $weather_data[$key] = $weather_data[$sensors[$key]];
        } else {
            // Pokud není žádná vhodná náhrada, nastavíme hodnotu na 1
            $weather_data[$key] = 1;
        }
    }
}

// INSERT into Weather_table
$sql = "INSERT INTO $table_name (time";
foreach ($sensors as $column_name => $sensor_key) {
    $sql .= ", $column_name";
}
$sql .= ") VALUES (?,";
foreach ($sensors as $column_name => $sensor_key) {
    $sql .= ",";
}
$sql = rtrim($sql, ",") . ")";

$stmt = $conn->prepare($sql);
$stmt->bind_param("s", $time);
foreach ($sensors as $column_name => $sensor_key) {
    $stmt->bind_param("s", $weather_data[$sensor_key]);
}

if ($stmt->execute()) {
    echo "New record created successfully"."</br>";
} else {
    echo "Error: " . $sql . "<br>" . $conn->error;
}

$conn->close();
?>
