<!--Scripts to process forms and what not -->
	//Check if turn
	is_turn = false;
	if (({{counter}}%{{user_count}}+2)=={{user.id}}){
		is_turn = true;
		}
	
	//Socket Connection
	var socket = io.connect('http://localhost:1337');
	socket.on('connect', function() {

	});
	socket.on('disconnect', function() {
	});
	
	//Chat
	socket.on('nicknames', function(nicknames){
		$('#online').empty().append($('<span>Online:</span>'));
		for (var i in nicknames){
			$('#online').append($('<b>').text(nicknames[i]));
			}
	});
	
	//**Socket Block of Code **//
	
	socket.on('{{draft_id}}', function(message){
   		//Parse JSON
   		jp = JSON.parse(message)
   		
   		if ((jp.counter%{{user_count}}+2)=={{user.id}}){
   			is_turn = true;
   		}
   		else {
   			is_turn = false;
   		}   		
   		//If draft is done, redirect to end of draft page
   			//Create end of draft view
   		if (jp.counter >= {{end}}){
   		$(wrap).remove()
   		finished = '<h1>Draft Finished, please click here <a href="../../../bizarro/teams">Draft Results</a></h1>'
   		$('body').append(finished)
   		}

		//Add drafted player to drafted player list
		info = '<tr><td>' + jp.fantasy_name + '</td><td>' + jp.first_name + ' ' + jp.last_name + '</td><td>' + jp.position + '</td></tr>'
		$(info).appendTo('#drafted_players')
			
		//Delete drafted player from available player list
		id = 'tr#' + jp.player_id
		$(id).remove()
			
		//Timestamp

   			//Add amount of time to draft (set in beginning)
   		draft_by_time = Math.round(jp.time_stamp)+{{round_time}}
   		
 			//Find current time
 		var current = new Date();  		
 		current_time = Math.round(current.getTime()/1000)
 		
 			//Time until draft pick is due (Draft by time - current time)
   		time_until_pick = draft_by_time - current_time;
   		
   		//Update turns
		
			//Alert its players turn
			//Add submit button
		if (is_turn){
			alert_message = '<h1 class="alert_message">Its your turn!</h1>'
			submit_button = '<input type="submit" class="submit_button" value="draft"/' + '>'
			$(alert_message).appendTo('#alert')
			$(submit_button).appendTo('#submit')
			change_title()
   			}
   			
		//Clear alert and message if not turn
		else{
			$('.alert_message').remove()
			$('.submit_button').remove()
		}
	});
	//**End of Socket Code **//
	
	
	//AJAX  form submission
	$('#myform').submit(function(event){
		//Radio Checked Value
		player_id = $('input:radio[name=player_id]:checked').val()
						
		//Prevent Submit From Working
		event.preventDefault();
			
		//Submit to /bizarro/draft/ with variables player_id
		$.post('/bizarro/draft/{{draft_id}}/', {'player_id':player_id})
	});
	
	
	//Countdown_timer
		//Get the last draft time from django
   	var last_draft_time = {{stamp}}
   	
   		//Add to it the amount of time per pick
   	draft_by_time = Math.round(last_draft_time)+{{round_time}}
   	
   		//Get current time
   	var current = new Date();
   	current_time = Math.round(current.getTime()/1000)
   	
   		//Time until pick is time until draft - current time
   	time_until_pick = draft_by_time - current_time;
	
	
	//Countdown mechanism code
	function countdown(){
		time_until_pick -=1
		minute = Math.floor(time_until_pick/60)
		seconds = time_until_pick%60
		if (seconds < 10){
			seconds = '0'+seconds
		}
		time = '' + minute + ':' + seconds
		$('#timer').html(time)
		if (time_until_pick<1 && is_turn){
		select_player()
		}
	}
	
	//Calls countdown function at a 1 second rate
	setInterval("countdown()", 1000)
	
	
	
	//Code to automatically select a player
  	function select_player(){
   		//Right now just drafts the last player available, probably fine but could be based on rank or user preference
   		//Figure out how to randomize that
   		
   		player_id = $('input:radio[name=player_id]').last().val()
   		$.post('/bizarro/draft/{{draft_id}}/', {'player_id':player_id})
   		}	
   		
	//Change title if turn
	function change_title(){
	var isOldTitle = true;
	var oldTitle = "Draft";
	var newTitle = "Your turn!";
	var interval = null;
	clearInterval(interval);
	function changeTitle() {
		if (is_turn){
    	document.title = isOldTitle ? oldTitle : newTitle;
    	isOldTitle = !isOldTitle;
	}
	else{
	document.title = 'Draft'
	}}
	interval = setInterval(changeTitle, 1000);
	$(window).focus(function () {
    	clearInterval(interval);
   		$("title").text('Draft');
	});
	$('body').click(function () {
		clearInterval(interval);
		$('title').text('Draft');
	});
	}

	//Chatbox
	
	//Function to add a message
	function message (from, msg) {
		if(from !='{{user_team_name}}'){
 		$('ul#chat_message').append($('<li>').append($('<b>').text(from), msg));
	}}
	
	//Send Username over nickname
	socket.emit("nickname",{'id':{{user.id}}, 'nickname':'{{user_team_name}}'});
	
	//Send Chat message over chat
	socket.on('chat', message);
	
	//When getting nickanme add it to online status
	socket.on('nicknames', function (nicknames) {
        $('#nicknames').empty().append($('<span>Online: </span>'));
        for (var i in nicknames) {
          $('#nicknames').append($('<b>').text(nicknames[i]));
        }
      });
      
	$input = $('input#chat')
	
	//On click of chat send add the message on my screen and send to everyone
	$('button').click(function(){
		//Send own message to me
		message('me', $input.val())
		//Send chat message on chat to everyone
		socket.emit('chat', $input.val())
		//Clear input
		$input.val('').focus()
	});
