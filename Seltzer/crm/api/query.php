<?php
////////////////////////////////
//This is the REST web service that will give back info from the Seltzer DB.
////////////////////////////////
//Josh Pritt  ramgarden@gmail.com
//Created: February 17, 2015

//This function cleans the input from
// malicious strings and returns the clean
// version.  There might be a better way
// to do this but this works for the most
// part.  :/
function testInput($data)
{
	$data = trim($data);
	$data = stripslashes($data);
	$data = htmlspecialchars($data);
	return $data;
}

//This function takes in an RFID alpha numeric string 
//and a comma separated list of field names to return.
//The RFID belongs to the member and the fields are the 
//ones you want to have back.
function getMemberInfoByRFID($rfid, $fieldNames)
{
	require('db.inc.php');

	$rfid = testInput($rfid);
	$fieldNames = testInput($fieldNames);

	$memberInfo = array();

	if ($fieldNames == "") {
		$fieldNames = "*";
	}

	//first build the query
	$query = "SELECT " . $fieldNames . " FROM 
			(
			`key` k
			LEFT JOIN  `contact` c ON k.cid = c.cid
			)
			WHERE k.serial = '" . $rfid . "'";

	//then get the matching member
	$result = mysqli_query($con, $query)
		or die(json_encode(array("getMemberInfoByRFIDQueryERROR" => mysql_error())));

	//then stick the member info into an assoc array
	$memberInfo = mysqli_fetch_assoc($result);

	return $memberInfo;
}

//This function returns the unix timestamp of the last payment made
// for the member with the given RFID.
function getMemberLastPaymentTimestamp($rfid)
{
	require('db.inc.php');

	$rfid = testInput($rfid);

	$memberInfo = array();

	//first see if the key is even in the system.
	//We could just do a big join all at once but we wouldn't know
	// if the key or the member was not found, etc.
	$query = "SELECT cid FROM `key` WHERE serial = '" . $rfid . "'";

	//then get the matching member
	$result = mysqli_query($con, $query)
		or die(json_encode(array("getKeyQueryERROR" => mysql_error())));

	$keyRow = mysqli_fetch_assoc($result);

	if ($keyRow == 0) {
		return array("ERROR" => "No key found for RFID: " . $rfid);
	}

	//then get the last payment entered for this member
	$query = "SELECT UNIX_TIMESTAMP(MAX(date)) FROM payment WHERE value > 0 and credit = " . $keyRow['cid'];

	$result = mysqli_query($con, $query)
		or die(json_encode(array("getPaymentQueryERROR" => mysql_error())));

	$paymentInfo = mysqli_fetch_array($result);

	$timestamp = $paymentInfo[0];

	if ($timestamp == NULL) {
		return array("ERROR" => "No payments found for key owner.");
	}

	$iso8601 = date('c', $timestamp);

	$jsonResponse = array("timestamp" => $timestamp, "iso8601" => $iso8601);
	return $jsonResponse;
}

//action=getRFIDWhitelist
//returns JSON array of all key serial values for all members who owe less than 2 months
// of their monthly plan's dues.
function getRFIDWhitelist()
{
	require('db.inc.php');
	$db_connect = $con;

	$whiteList = array();

	//get everyone's plan prices and balances and check here
	$balances = payment_accounts();
	foreach ($balances as $cid => $bal) {
		//now get this member's monthly plan amount
		$memberData = member_data(array("cid" => $cid));
		$planAmount = $memberData[0]["membership"][0]["plan"]["price"];
		$firstName = $memberData[0]["contact"]["firstName"];
		$lastName = $memberData[0]["contact"]["lastName"];
		$memberBalance = $bal['value'] / 100;
		if ($memberBalance <= ($planAmount * 2) || $memberBalance == 0) {
			//this member has paid their dues. Add to whitelist.
			//get their key serial and add that too!
			$query = "SELECT serial FROM `key` WHERE char_length(serial) > 5 and cid = " . $cid;
			$result = mysqli_query($con, $query)
				or die(json_encode(array("getRFIDWhitelistQueryERROR" => mysqli_error($con))));
			$r = mysqli_fetch_assoc($result);
			$serial = $r["serial"];
			if ($serial != NULL) {
				$whiteList[] = array("serial" => $serial);
			}
		}
	}

	return $whiteList;
}

//action=doorLockCheck&rfid=<scanned RFID>
//returns JSON string TRUE if key owner has a balance less than 2 times
// their current montly plan price, FALSE or error string if not.
function doorLockCheck($rfid)
{
	require('db.inc.php');
	$db_connect = $con;

	$rfid = testInput($rfid);

	//get the key owner and their current membership plan
	$query = "SELECT c.cid, p.price
				FROM ((
				`key` k
				LEFT JOIN  `contact` c ON k.cid = c.cid
				)
				LEFT JOIN `membership` m ON m.cid = c.cid
				)
				LEFT JOIN `plan` p ON p.pid = m.pid
				where k.serial = '" . $rfid . "'";

	$result = mysqli_query($con, $query)
		or die(json_encode(array("doorLockCheckQueryERROR" => mysqli_error($con))));

	//if no rows returned then that key wasn't even found in the DB
	if (mysqli_num_rows($result) == 0) {
		$jsonResponse = array("key " . $rfid . " not found in db");
	} else {
		$row = mysqli_fetch_assoc($result);

		$memberID = $row["cid"];
		$planPrice = $row["price"];

		$accountData = payment_accounts(array("cid" => $memberID));
		//{"2":{"credit":"2","code":"USD","value":5000}}

		$memberBalance = $accountData[$memberID]["value"] / 100;

		//if the current key owner's balance is 
		// greater than 2 months of dues then access is denied!
		// Unless thier plan price is zero then 0 balance == 0 price is OK.
		if ($memberBalance > ($planPrice * 2) && $memberBalance > 0) {
			$jsonResponse = array("member balance = " . $memberBalance);
		} else {
			$jsonResponse = array("True");
		}
	}

	return $jsonResponse;
}

//action=getAccessLog
//returns JSON array of the last 7 days of card access
function getAccessLog()
{
	//date_default_timezone_set('America/Phoenix'); // timezone of the server
	//$date = new DateTime($input, new DateTimeZone('America/New_York')); // USER's timezone
	//$date->setTimezone(new DateTimeZone('UTC'));
	//echo $date->format('Y-m-d H:i:s');

	$query = "SELECT accesslog.id, contact.cid, CONCAT( firstname,  ' ', lastname ) AS member, access, reason, swipetime 
			FROM accesslog
			LEFT JOIN `key` ON accesslog.serial = key.serial
			LEFT JOIN contact ON key.cid = contact.cid
			where swipetime >= DATE_ADD(curdate(),INTERVAL -7 DAY) 
			ORDER BY swipetime desc";

	return runSqlQuery($query, "-4:00");
}

//action=logDoorAccess&rfid=<scanned RFID>
//returns JSON string TRUE if logged the key swipe to the DB OK.
//returns JSON ERROR object if there was a problem.
//This function inserts a row into the ACCESSLOG table with the
// scanned RFID serial and the timestamp when it was swiped.
function logDoorAccess($rfid, $access = 1, $reason)
{
	if (!$access) { $access = 1;  }
	if (!$reason)
		$query = "INSERT into accesslog (serial,access) values ('$rfid',$access)";
	else
		$query = "INSERT into accesslog (serial,access,reason) values ('$rfid',$access,'$reason')";
        
	require('db.inc.php');

	$result = mysqli_query($con, $query)
		or die(json_encode(array("getERROR" => mysqli_error($con))));

	return array("True");
}

//set timezone parameter if you want to query out any date or timestamp fields.
function runSqlQuery($query, $timezone = "")
{
	require('db.inc.php');

	$ArrayToReturn = array();

	if (strlen($timezone) > 0) {
		$statement = "SET time_zone = '" . $timezone . "';";
		mysqli_query($con, $statement);
	}

	$result = mysqli_query($con, $query)
		or die(json_encode(array("getERROR" => mysqli_error($con))));

	if (is_object($result)) {
		$finfo = $result->fetch_fields();

		while ($r = mysqli_fetch_assoc($result)) {
			$currentRecord = array();

			foreach ($finfo as $val) {
				$currentRecord[$val->name] = $r[$val->name];
			}

			$ArrayToReturn[] = $currentRecord;
		}
		$result->close();
	}

	return $ArrayToReturn;
}

//////////////////////////////////////
//other functions for service go here. 
// don't forget to add the action to the 
// $possible_url array below!!!!!
//You will then have to add the entry for
// the switch case below as well.
//////////////////////////////////////


$possible_url = array(
	"getMemberInfoByRFID",
	"getMemberLastPaymentTimestamp",
	"getRFIDWhitelist",
	"otherFunctionName",
	"doorLockCheck",
	"getAccessLog",
	"logDoorAccess"
);

$value = "An error has occurred";

if (isset($_GET["action"]) && in_array($_GET["action"], $possible_url)) {
	switch ($_GET["action"]) {
		case "getMemberInfoByRFID":
			$value = getMemberInfoByRFID($_GET['rfid'], $_GET['fieldNames']);
			break;
		case "getMemberLastPaymentTimestamp":
			$value = getMemberLastPaymentTimestamp($_GET['rfid']);
			break;
		case "getRFIDWhitelist":
			$value = getRFIDWhitelist($_GET['fields']);
			break;
		case "doorLockCheck":
			$value = doorLockCheck($_GET['rfid']);
			break;
		case "getAccessLog":
			$value = getAccessLog();
			break;
		case "logDoorAccess":
			$value = logDoorAccess($_GET['rfid'], $_GET['access'], $_GET['reason']);
			break;
		case "get_app":
			if (isset($_GET["id"]))
				$value = get_app_by_id($_GET["id"]);
			else
				$value = "Missing argument";
			break;
	}
}

//return JSON object as the response to client
exit(json_encode($value));
?>