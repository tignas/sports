$(document).ready(function () {
    var url = 'http://search.twitter.com/search.json?callback=?';
    var query = encodeURIComponent('{{player.person.names[0]}}');
    var data = {
        q: query,
        rpp: 100,
        include_entities: 'true',
        result_type: 'mixed',
        exclude: 'retweets',
    }
    
    $.getJSON(url, data, function(response) {
        console.log(response)
        $.each(response.results, function(i, tweet) {
            var user_handle = tweet.from_user,
                user_name = tweet.from_user_name,
                image_url = tweet.profile_image_url,
                text = tweet.text,
                time = tweet.created_at,
                id_str = tweet.id_str;
            var entities = ['hashtags', 'urls', 'user_mentions'];
            $.each(entities, function(i, entity) {
                if (tweet.entities[entity].length > 0) {
                    var entity = tweet.entities[entity]
                }
            });
            var hashtags = tweet.entities.hashtags;
            if (hashtags.length > 0) {
                $.each(hashtags, function(i, hashtag) {
                    var href = 'http://twitter.com/i/#!/search/?q=%23' + hashtag.text + '&src=hash';
                    var hash_link = "<a href='" + href + "'>#" + hashtag.text + "</a>";
                    text = text.replace('#' + hashtag.text, hash_link);
                    
                });
            };
            var urls = tweet.entities.urls;
            if (urls.length > 0) {
                $.each(urls, function(i, url) {
                    var url_link = "<a href='" + url.url + "'>" + url.display_url + "</a>";
                    text = text.replace(url.url, url_link);
                });
            };
            var user_mentions = tweet.entities.user_mentions;
            if (user_mentions.length > 0) {
                $.each(user_mentions, function(i, user_mention) {
                    var href = "<a class='user_mention' href='http://twitter.com/" + user_mention.screen_name + "'>@" + user_mention.screen_name + "</a>"
                    text = text.replace('@' + user_mention.screen_name, href);
                });
            };            
            var tweet_date = new Date(Date.parse(time));
            var now = new Date();
            var time_ago = (now.getTime() - tweet_date.getTime())/1000;
            if (time_ago < 0) {
                time_ago = 'now';
            } else if (time_ago < 60) {
                time_ago = Math.floor(time_ago) + 's';
            } else if (time_ago < 60*60) {
                time_ago = Math.floor(time_ago/(60)) + 'm';
            } else if (time_ago < 60*60*24) {
                time_ago = Math.floor(time_ago/(60*60)) + 'h';
            } else {
                var monthNames = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ];
                time_ago = tweet_date.getUTCDate() + ' ' + monthNames[tweet_date.getMonth()];
            }
            var user_href = "href='http://twitter.com/" + user_handle + "'";
            var tweet_html = "<div class='tweet'>" +
                            "<a class='twitter_time' href='http://twitter.com/" + user_handle + '/status/' + id_str + "'>" + time_ago + "</a>" +
                            "<a class='avatar'" + user_href + "><img src='" + image_url + "'/>" + "</a>" +
                            "<span class='twitter_user_info'>" +
                            "<a class='user_name'" + user_href + ">"+ user_name + "</a><br />" +
                            "<a class='user_handle'" + user_href + ">@" + user_handle + "</a>" +
                            "</span>" + 
                            "<span class='twitter_text'>" + text + "</span>" +
                            "<a class='reply' href='http://twitter.com/intent/tweet?in_reply_to=" + id_str + "'>Reply</a>" + 
                            "<a class='retweet' href='http://twitter.com/intent/retweet?tweet_id=" + id_str + "'>Retweet</a>" + 
                            "<a class='favorite' href='http://twitter.com/intent/favorite?tweet_id=" + id_str + "'>Favorite</a>" +
                            "</div>";
                            
            $('#tweets').append(tweet_html);
        });
    });
    
});
