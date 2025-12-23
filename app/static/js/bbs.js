function repost_no(num,hidden_num){
    const elm = document.getElementById("parent_post_id");
    elm.value = num;
    document.getElementById("parent_post_id_hidden").value = hidden_num;
    window.scrollTo( {top: elm.offsetTop, behavior:'smooth'});

	}