<!DOCTYPE html>
<html>
<meta charset="utf-8">
<head>
<style type="text/css">

  @media print {
    body {
      zoom: 65%;
    }
    @page {
      size: landscape;
    }
  }
  table {
  font-family: sans-serif;
  width: 100%;
  border-spacing: 0;
  border-collapse: separate;
  table-layout: fixed;
  margin-bottom: 50px;
}
table thead tr th {
  background: #626E7E;
  color: #d1d5db;
  padding: 0.5em;
  overflow: hidden;
}
table thead tr th:first-child {
  border-radius: 3px 0 0 0;
}
table thead tr th:last-child {
  border-radius: 0 3px  0 0;
}
table thead tr th .day {
  display: block;
  font-size: 1.2em;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  margin: 0 auto 5px;
  padding: 5px;
  line-height: 1.8;
}
table thead tr th .day.active {
  background: #d1d5db;
  color: #626E7E;
}
table thead tr th .short {
  display: none;
}
table thead tr th i {
  vertical-align: middle;
  font-size: 2em;
}
table tbody tr {
  background: #ffffff;
}
table tbody tr:nth-child(odd) {
  background: #ffffff;
}
table tbody tr:nth-child(4n+0) td {
  border-bottom: 1px solid #626E7E;
}
table tbody tr td {
  text-align: center;
  vertical-align: middle;
  border-left: 1px solid #626E7E;
  position: relative;
  height: 32px;
  cursor: pointer;
}
table tbody tr td:last-child {
  border-right: 1px solid #626E7E;
}
table tbody tr td.hour {
  font-size: 2em;
  padding: 0;
  color: #626E7E;
  background: #fff;
  border-bottom: 1px solid #626E7E;
  border-collapse: separate;
  min-width: 100px;
  cursor: default;
}
table tbody tr td.hour span {
  display: block;
}
@media (max-width: 60em) {
  table thead tr th .long {
    display: none;
  }
  table thead tr th .short {
    display: block;
  }
  table tbody tr td.hour span {
    transform: rotate(270deg);
    -webkit-transform: rotate(270deg);
    -moz-transform: rotate(270deg);
  }
}
@media (max-width: 27em) {
  table thead tr th {
    font-size: 65%;
  }
  table thead tr th .day {
    display: block;
    font-size: 1.2em;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    margin: 0 auto 5px;
    padding: 5px;
  }
  table thead tr th .day.active {
    background: #d1d5db;
    color: #626E7E;
  }
  table tbody tr td.hour {
    font-size: 1.7em;
  }
  table tbody tr td.hour span {
    transform: translateY(16px) rotate(270deg);
    -webkit-transform: translateY(16px) rotate(270deg);
    -moz-transform: translateY(16px) rotate(270deg);
  }
}

</style>
</head>
<body>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<p>
  <b>Period</b>:  {{ start_date.strftime('%d/%b/%y') }} - {{ end_date.strftime('%d/%b/%y') }}
</p>
<table>
  <thead>
    <tr>
      <th></th>
      <th>
        <span class="long">Breakfast</span>
        <span class="short">Breakfast</span>
      </th>
      <th>
        <span class="long">Lunch</span>
        <span class="short">Lunch</span>
      </th>
      <th>
        <span class="long">Dinner</span>
        <span class="short">Dinner</span>
      </th>
    </tr>
  </thead>
  <tbody>
  {% for item in schedule %}
    <tr>

      <td class="hour" rowspan="4"><span>{{ calendar.day_abbr[loop.index-1] }}</span></td>
      <td>{{ item['breakfast'] }}</td>
      <td>{{ item['lunch'] }}</td>
      <td>{{ item['dinner'] }}</td>
    </tr>
    <tr>
      <td>उबला हुआ अंडा - 2</td>
      <td>सलाद</td>
      <td></td>
    </tr>
    <tr>
      <td>गर्म दूध - 1 पैकेट</td>
      <td>रोटी - 3</td>
      <td></td>
    </tr>
    <tr>
      <td></td>
      <td></td>
      <td></td>
    </tr>

  {% endfor %}
  </tbody>
</table>
<div>
  <b>Inventory</b>:
  {% for item in inventory %}
  <span>{{ item }}{% if not loop.last %},{% endif %}</span>
  {% endfor %}
</div>
</body>
</html>
