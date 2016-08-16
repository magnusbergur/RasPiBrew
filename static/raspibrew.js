
//declare globals
var tempDataArray, heatDataArray, setpointDataArray, dutyCycle, options_temp, options_heat, plot, showLines, sensorValues, rowSelected = 1;
var capture_on = 1;
var numTempSensors, temp, setpoint, captureWindowSize, areSensorsSet = 0; 

function GPIOChange(IOnr, checked){
	var status, btnNewClass, btnOldClass
	if (checked){
		status = "on"
		btnNewClass = "btn-success"
		btnOldClass = "btn-danger"
	} else {
		status = "off"
		btnNewClass = "btn-success"
		btnOldClass = "btn-danger"
	}

	jQuery.ajax({
		type : "GET",
		url : "/GPIO_Toggle/"+IOnr+"/"+status,
		dataType : "json",
		async : true,
		cache : false,
		timeout : 50000,
		success : function(data) {
			$("#GPIO_label"+IOnr).attr('title', 'Switch controls pin '+data.pin);
			if (data.status == status) {	
				if ($("#GPIO_Color"+IOnr).hasClass(btnOldClass)) {
					$("#GPIO_Color"+IOnr).removeClass(btnOldClass);
					$("#GPIO_Color"+IOnr).addClass(btnNewClass);
				}
			}
		},
	});
}

$("#GPIO1").change(function() {
	GPIOChange(1, this.checked)
});

$("#GPIO2").change(function() {
	GPIOChange(2, this.checked)
});

$(window).unload(function() {
	cacheData();
    console.log('Cached data');
});

function showTooltip(x, y, contents)
{
	jQuery('<div id="tooltip">' + contents + '</div>').css({
		position : 'absolute',
		display : 'none',
		top : y + 5,
		left : x + 5,
		border : '1px solid #fdd',
		padding : '2px',
		'background-color' : '#fee',
		opacity : 0.80
	}).appendTo("body").fadeIn(200);
}

function pushData(timeseries, timestamp, value) {
	timeseries.push([timestamp, parseFloat(value)]);
	while (timeseries.length > captureWindowSize) {
		timeseries.shift();
	}
}

function storeData(index, data)
{
	var timestamp = Date.now();
	pushData(tempDataArray[index], timestamp, data.temp)

	if (data.mode == "auto") {
		pushData(setpointDataArray[index], timestamp, data.set_point)
	}
	
	if(index == 0) {
		pushData(heatDataArray[index], timestamp, data.duty_cycle)
	}

	sensorValues[index].mode = data.mode;
	sensorValues[index].setpoint = data.set_point;
	sensorValues[index].dutycycle = data.duty_cycle;
	sensorValues[index].cycletime = data.cycle_time;
	sensorValues[index].k = data.k;
	sensorValues[index].i = data.i;
	sensorValues[index].d = data.d;
}

function plotData()
{
	var hlt_series     = { label: "HLT",     data: tempDataArray[0] };
	var hlt_set_series = { label: "HLT-set", data: setpointDataArray[0] };
	var mlt_series     = { label: "MLT",     data: tempDataArray[1] };
	var mlt_set_series = { label: "MLT-set", data: setpointDataArray[1] };
	var bk_series      = { label: "BK",      data: tempDataArray[2] };
	var basedata = [hlt_series, hlt_set_series, mlt_series, mlt_set_series, bk_series]

	data = []
	for (i = 0; i < 5; i++) {
		if (showLines[i] == 1){
			data.push(basedata[i])
		}
	}

	plot = jQuery.plot($("#tempplot"), data, options_temp);
	plot = jQuery.plot($("#heatplot"), [heatDataArray[0]], options_heat);
}

//long polling - wait for message
function waitForMsg()
{
	for (s = 0; s < 3; s++)
	{
		jQuery.ajax({
			type : "GET",
			url : "/getstatus/"+(s+1),
			dataType : "json",
			async : true,
			cache : false,
			timeout : 50000,

			success : function(data)
			{
				var sensor = data.sensor;
				jQuery('#tempResponse'+sensor).html(data.temp);
				jQuery('#setpointResponse'+sensor).html(data.set_point);
				jQuery('#dutycycleResponse'+sensor).html(data.duty_cycle.toFixed(2));

				storeData(sensor-1, data);

				if (capture_on == 1 && sensor == 1)
				{
					plotData();
					setTimeout('waitForMsg()', 1); //in millisec
				}
			}
		});
	}
};

function initializeData() {
	console.log( "Initialize data" );
	showLines = [1,1,1,1,1];
	captureWindowSize = 1000000
	sensorInit = {mode : "off", setpoint : 0, dutycycle : 0, cycletime : 0, k : 0, i : 0, d : 0};
	sensorValues = [sensorInit,sensorInit,sensorInit,sensorInit];
	resetPlotData();

	document.getElementById("windowSizeText").value = captureWindowSize;
}

function resetPlotData() {
	console.log( "reset plot data" );
	tempDataArray = [[], [], [], []];
	heatDataArray = [[]];
	setpointDataArray = [[], []];
	cacheData();
}

function retrieveData() {
	console.log( "Retrieve data" );
	tempDataArray = JSON.parse(localStorage.getItem("tempDataArrayStore"));
	heatDataArray = JSON.parse(localStorage.getItem("heatDataArrayStore"));
	setpointDataArray = JSON.parse(localStorage.getItem("setpointDataArrayStore"));
	showLines = JSON.parse(localStorage.getItem("showLines"));
	sensorValues = JSON.parse(localStorage.getItem("sensorValues"));	
	captureWindowSize = JSON.parse(localStorage.getItem("cacheWindowSizeStore"));	
	console.log('History size: '+tempDataArray[0].length)

	document.getElementById("windowSizeText").value = captureWindowSize;
}

function cacheData() {
	console.log( "Cache data" );
	localStorage.setItem("tempDataArrayStore", JSON.stringify(tempDataArray))
	localStorage.setItem("heatDataArrayStore", JSON.stringify(heatDataArray));
	localStorage.setItem("setpointDataArrayStore", JSON.stringify(setpointDataArray));
	localStorage.setItem("showLines", JSON.stringify(showLines));
	localStorage.setItem("sensorValues", JSON.stringify(sensorValues));
	localStorage.setItem("cacheWindowSizeStore", JSON.stringify(captureWindowSize));
}

function setPIDParams(idx) {
	$('.modeBtn').removeClass("active");
	$('#modeBtn_'+sensorValues[idx].mode).addClass('active');
	$('#mode_'+sensorValues[idx].mode).prop('checked', true);

	$('#setpoint').val(sensorValues[idx].setpoint);
	$('#dutycycle').val(sensorValues[idx].dutycycle);
	$('#cycletime').val(sensorValues[idx].cycletime);
	$('#kc_param').val(sensorValues[idx].k);
	$('#ti_param').val(sensorValues[idx].i);
	$('#td_param').val(sensorValues[idx].d);
}

function selectLinesToShow()  {
	for (l = 1; l < 6; l++) {
		if(showLines[l-1] == 0) {
			$('#Chbx'+l).prop('checked', false);
		}	
	}
}  

jQuery(document).ready(function() {

	jQuery('#stop').click(function() {
		capture_on = 0;
	});
	jQuery('#restart').click(function() {
		capture_on = 1;
		resetPlotData()
		console.log( "restart plot" );
		waitForMsg();
	});

	var previousPoint = null;
	jQuery("#tempplot").bind("plothover", function(event, pos, item) {
		if (item) {
			if (previousPoint != item.dataIndex) {
				previousPoint = item.dataIndex;

				jQuery("#tooltip").remove();
				var x = item.datapoint[0].toFixed(2), y = item.datapoint[1].toFixed(2);

				showTooltip(item.pageX, item.pageY, "(" + x + ", " + y + ")");
			}
		} else {
			jQuery("#tooltip").remove();
			previousPoint = null;
		}

	});

	$("#ToggleLines").find("input[type='checkbox']").click(function () {
	    var position = $(this).attr("id").replace("Chbx", "");
	    position = parseInt(position) - 1;
	    
	    if ($(this).is(":checked")) {
	        showLines[position] = 1;
	    } else {
			showLines[position] = 0;
	    }
    });

    $('.selectRow').click(function() {
		$('.selectRow').removeClass("row-highlight");
		// removes all the highlights from the table
		$(this).addClass('row-highlight');

		var position = $(this).attr("id").replace("TblRow", "");
	    rowSelected = parseInt(position);
	    
	    console.log("selectRow "+rowSelected)
	    setPIDParams(rowSelected-1);
	});

	jQuery('#controlPanelForm').submit(function() {

		if(rowSelected > 0)
		{
			formdata = jQuery(this).serialize();

			jQuery.ajax({
			type : "POST",
			url : "/postparams/"+rowSelected,
			data : formdata,
			success : function(data) {
			},
		});
		}

		return false;
	});

	if(document.cookie.indexOf('mycookie')==-1){
	    document.cookie = 'mycookie=1';

    	initializeData()
	} else {
		//initializeData()
	    retrieveData();
	}
	selectLinesToShow();

	jQuery('#windowSizeText').change(function() {
		console.log( "windowSizeText changed" );
		captureWindowSize = jQuery('#windowSizeText').val()
	});

	options_temp = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : null,
			max : null
		},
		xaxis : {
			show : true,
			mode : "time"
		},
		grid : {
			hoverable : true
			//  clickable: true
		},
		selection : {
			mode : "x"
		},
		legend : {
			position: "nw"
		}

	};

	options_heat = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : 0,
			max : 100
		},
		xaxis : {
			show : true,
			mode : "time"
		},
		selection : {
			mode : "x"
		}
	};

	waitForMsg();

});
