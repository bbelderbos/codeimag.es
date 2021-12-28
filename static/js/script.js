const boxes = document.querySelectorAll(".box, footer, footer a");
const darkIsTurnedOn = localStorage.getItem('darkModeIsOn');

function turnOnDarkMode(){
  localStorage.setItem('darkModeIsOn', 'true');
  boxes.forEach(box => {
    box.style.backgroundColor = "#343a40"
    box.style.color = "#fff"
  });
}

function turnOffDarkMode(){
  localStorage.setItem('darkModeIsOn', 'false');
  boxes.forEach(box => {
    box.style.backgroundColor = "#fff"
    box.style.color = "#343a40"
  });
}


$(function() {

  $('.copyCode').click(function() {
    let copyText = $(this).siblings()[1].innerText;
    // https://stackoverflow.com/a/67758578
    navigator.clipboard.writeText(copyText).then(function(){
      alert("Code copied to clipboard.");
    });
    return false;
  })

  // persist dark mode
  if(darkIsTurnedOn === 'true'){
    $('#toggleDarkMode').prop('checked', true).change();
    turnOnDarkMode();
  } else {
    $('#toggleDarkMode').prop('checked', false).change();
    turnOffDarkMode();
  }

  $('#toggleDarkMode').change(function() {
    if($(this).prop('checked')){
      turnOnDarkMode();
    } else {
      turnOffDarkMode();
    }
  })

})
