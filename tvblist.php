<?php

$CHANNEL_LIST = array(
    'J' => array(
   'name' => '翡翠台',
   'license' => '0958b9c657622c465a6205eb2252b8ed:2d2fd7b1661b1e28de38268872b48480',
   'logo' => 'https://github.com/wanglindl/TVlogo/blob/main/img/TVB1.png?raw=true'
    ),
    'JUHD' => array(
   'name' => '翡翠台 4K',
   'license' => '2c045f5adb26d391cc41cd01f00416fa:fc146771a9b096fc4cb57ffe769861be',
   'logo' => 'https://github.com/wanglindl/TVlogo/blob/main/img/TVB1.png?raw=true'
    ),
    'B' => array(
   'name' => 'TVBplus',
   'license' => '56603b65fa1d7383b6ef0e73b9ae69fa:5d9d8e957d2e45d8189a56fe8665aaaa',
   'logo' => 'https://raw.githubusercontent.com/wanglindl/TVlogo/main/img/TVB3.png'
    ),
    'P' => array(
   'name' => '明珠台',
   'license' => 'e04facdd91354deee318c674993b74c1:8f97a629de680af93a652c3102b65898',
   'logo' => 'https://github.com/wanglindl/TVlogo/blob/main/img/TVB1.png?raw=true'
    ),
    'CWIN' => array(
   'name' => 'Super Free',
   'license' => '0737b75ee8906c00bb7bb8f666da72a0:15f515458cdb5107452f943a111cbe89',
   'logo' => ''
    ),
    'TVG' => array(
   'name' => '黄金翡翠台',
   'license' => '8fe3db1a24969694ae3447f26473eb9f:5cce95833568b9e322f17c61387b306f',
   'logo' => 'https://github.com/sparkssssssssss/epg/blob/main/logo/%E9%BB%84%E9%87%91%E7%BF%A1%E7%BF%A0%E5%8F%B0.png?raw=true'
    ),
    'C' => array(
   'name' => '无线新闻台',
   'license' => '90a0bd01d9f6cbb39839cd9b68fc26bc:51546d1f2af0547f0e961995b60a32a1',
   'logo' => 'https://raw.githubusercontent.com/wanglindl/TVlogo/main/img/TVB4.png'
    ),
    'CTVE' => array(
   'name' => '娱乐新闻台',
   'license' => '6fa0e47750b5e2fb6adf9b9a0ac431a3:a256220e6c2beaa82f4ca5fba4ec1f95',
   'logo' => 'https://github.com/sparkssssssssss/epg/blob/main/logo/%E5%A8%B1%E4%B9%90%E6%96%B0%E9%97%BB%E5%8F%B0.png?raw=true'
    ),
    'PCC' => array(
   'name' => '凤凰卫视中文台',
   'license' => '7bca0771ba9205edb5d467ce2fdf0162:eb19c7e3cea34dc90645e33f983b15ab',
   'logo' => 'https://raw.githubusercontent.com/wanglindl/TVlogo/main/img/Phoenix1.png'
    ),
    'PIN' => array(
   'name' => '凤凰卫视资讯台',
   'license' => '83f7d313adfc0a5b978b9efa0421ce25:ecdc8065a46287bfb58e9f765e4eec2b',
   'logo' => 'https://raw.githubusercontent.com/wanglindl/TVlogo/main/img/Phoenix2.png'
    ),
    'PHK' => array(
   'name' => '凤凰卫视香港台',
   'license' => 'cde62e1056eb3615dab7a3efd83f5eb4:b8685fbecf772e64154630829cf330a3',
   'logo' => 'https://raw.githubusercontent.com/wanglindl/TVlogo/main/img/Phoenix3.png'
    ),
    'EVT1' => array(
   'name' => 'myTV SUPER直播足球1台',
   'license' => 'e8ca7903e25450d85cb32b3057948522:d5db5c03608f5f6c8a382c6abcb829e4',
   'logo' => ''
    )
);

function get_mytvsuper($channel) {
    global $CHANNEL_LIST;

    if (!array_key_exists($channel, $CHANNEL_LIST)) {
   return '频道代号错误';
    }

    $api_token = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJib3NzX2lkIjoiMTMzODkxNzE2IiwiZGV2aWNlX3Rva2VuIjoicFFGejNjQUx1RGVVRDE1TkxqTHRqd3ozIiwiZGV2aWNlX2lkIjoiWVRrMk5ESXpOemN0TlRNNU15MDBOREUxTFdGbFpqQXRPRGN4TkdFMFptSXhNalZqIiwiZGV2aWNlX3R5cGUiOiJ3ZWIiLCJkZXZpY2Vfb3MiOiJicm93c2VyIiwiZHJtX2lkIjoiWVRrMk5ESXpOemN0TlRNNU15MDBOREUxTFdGbFpqQXRPRGN4TkdFMFptSXhNalZqIiwiZXh0cmEiOnsicHJvZmlsZV9pZCI6MX0sImlhdCI6MTcxOTczNDQ0NiwiZXhwIjoxNzE5NzM4MDQ2fQ.i8RqU0z7SpIKQJ7KyyaeH3lbCTHXDicpF8rrw6iM5PilTz14HTY7E5gjhNt7lCrhCUXPOzP9-35bCs6hergRlVbI_00x3aFrQk1G9AAjwNxY5-fAH_bEjaS8oegeozu8wBxjQWJO9i26wRZuNTZ1SS9cBnkFNfzNaexCJ4cH2tRoXT41up2XvoFser7pnRcTEeOn7flVlQPA8pPk_TGhZGqGe-4B23929c5nXHcUQnlX_0z9BZZdQiUzsFpYNPX0jmcYJtUDkqTSG4J1fLiXuEpSqVbxpfS3T3qjZPtF0T0Idgdzjk2n_0yM4IH9its4VGT1T--ts17fffX5h5ZiDmOcyAfAGQkWcLYckxocnqNW5z4zY1UJiiBX0YMrf2pjmvIEziBMEbMz2eeY_VCRcTiu6LDhObgiKtnWmsKWPT9qE_yCeN5bOV6Vq14y77eh_4Fg83zITpFsYZAXYixod_vuMZtuTxnd5eiQkjOfTH-f_8nVbWbHUmOwBTMYS5fWuxdF57ZfcjzyhDSDZXLDGTkwW2rnCrsRsyS3eeEZu1rdOP1meTsxISO0x3QE_t4P9IuF-Nmj9AU-4HBYvJFPDD-bdH-7pr-6Q9KTnE4GT3_jZGOZ01D9zao6G8K83bJMIwGHQmec75qKxKewIUKXZCgvft0gMqg3hnfRG-OfctA'; // 请自行获取
    $headers = array(
   'Accept: application/json',
   'Authorization: Bearer ' . $api_token,
   'Accept-Language: zh-CN,zh-Hans;q=0.9',
   'Host: user-api.mytvsuper.com',
   'Origin: https://www.mytvsuper.com',
   'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15',
   'Referer: https://www.mytvsuper.com/',
   'X-Forwarded-For: 210.6.4.148'  // 香港原生IP  210.6.4.148
    );

    $params = array(
   'platform' => 'android_tv',
   'network_code' => $channel
    );

    $url = 'https://user-api.mytvsuper.com/v1/channel/checkout?' . http_build_query($params);
    $context = stream_context_create(array('http' => array('header' => implode("\r\n", $headers))));
    $response = file_get_contents($url, false, $context);

    if ($response === false) {
   return '请求失败';
    }

    $response_json = json_decode($response, true);
    $profiles = $response_json['profiles'];

    $play_url = '';
    foreach ($profiles as $profile) {
   if ($profile['quality'] === 'high') {
  $play_url = $profile['streaming_path'];
  break;
   }
    }

    if (empty($play_url)) {
   return '未找到播放地址';
    }

    $play_url = explode('&p=', $play_url)[0];

    $license_key =$CHANNEL_LIST[    $channel]['license'];
    $channel_name =$CHANNEL_LIST[    $channel]['name'];
    $channel_logo =$CHANNEL_LIST[    $channel]['logo'];
    $m3u_content = "#EXTINF:-1 tvg-id=\"" .$channel . "\" tvg-logo=\"" .$channel_logo . "\"," .$channel_name . "\n";
    $m3u_content .= "#KODIPROP:inputstream.adaptive.manifest_type=mpd\n";
    $m3u_content .= "#KODIPROP:inputstream.adaptive.license_type=clearkey\n";
    $m3u_content .= "#KODIPROP:inputstream.adaptive.license_key=" .$license_key . "\n";
    $m3u_content .=$play_url . "\n";

    return $m3u_content;
}

// 创建或打开文件用于写入
$m3u_file = fopen('mytvfree.m3u', 'w');

// 写入 M3U 文件的头部
fwrite($m3u_file, "#EXTM3U\n");

// 遍历所有频道并写入每个频道的 M3U 内容
foreach ($CHANNEL_LIST as $channel_code => $channel_info) {
    $m3u_content = get_mytvsuper($channel_code);
    fwrite($m3u_file, $m3u_content);
}

// 关闭文件
fclose($m3u_file);

echo "所有频道的 M3U 播放列表已生成并保存为 'mytvfree.m3u'。";

?>
